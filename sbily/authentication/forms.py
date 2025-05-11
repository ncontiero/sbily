from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from sbily.forms import BaseForm
from sbily.forms import BaseModelForm
from sbily.users.models import User
from sbily.utils.data import is_none
from sbily.utils.data import validate_password


class NextAndDestinationURLForm(BaseForm):
    next_path = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        initial="my_account",
    )
    destination_url = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    def clean_destination_url(self):
        destination_url = self.cleaned_data.get("destination_url")
        if not is_none(destination_url):
            url_validate = URLValidator()
            try:
                url_validate(destination_url)
            except ValidationError:
                destination_url = None
        return destination_url

    def clean_next_path(self):
        next_path = self.cleaned_data.get("next_path")
        if is_none(next_path):
            return reverse("my_account")
        if next_path.startswith("/"):
            return next_path

        try:
            reverse(next_path)
        except NoReverseMatch:
            next_path = reverse("my_account")

        return next_path


class SignUpForm(BaseModelForm, NextAndDestinationURLForm):
    plan = forms.CharField(
        widget=forms.HiddenInput(),
        max_length=50,
        initial="free",
        required=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "password"]
        required_fields = ["username", "email", "password"]
        widgets = {
            "password": forms.PasswordInput(),
        }

    def clean_password(self):
        password = self.cleaned_data.get("password")
        is_valid, message = validate_password(password)
        if not is_valid:
            raise forms.ValidationError(message, code="invalid_password")
        return password

    def save(self, commit=True):  # noqa: FBT002
        user = super().save(commit=False)
        user.set_password(user.password)
        if commit:
            user.save()
        return user


class SignInForm(NextAndDestinationURLForm):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(
        widget=forms.PasswordInput(),
        strip=False,
        required=True,
    )
    next_path = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        initial="my_account",
    )
    destination_url = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        user = authenticate(username=username, password=password)
        if user is None:
            msg = "Invalid credentials."
            raise forms.ValidationError(msg, code="invalid_credentials")

        cleaned_data["user"] = user
        return cleaned_data

    def clean_destination_url(self):
        destination_url = self.cleaned_data.get("destination_url")
        if not is_none(destination_url):
            url_validate = URLValidator()
            try:
                url_validate(destination_url)
            except ValidationError:
                destination_url = None
        return destination_url

    def clean_next_path(self):
        next_path = self.cleaned_data.get("next_path")
        if is_none(next_path):
            return "my_account"
        if next_path.startswith("/"):
            return next_path

        try:
            reverse(next_path)
        except NoReverseMatch:
            next_path = "my_account"

        return next_path


class BaseEmailForm(BaseForm):
    email = forms.EmailField(max_length=150, required=True)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        try:
            user = User.objects.get(email=email)
            if not user.email_verified:
                msg = "Please verify your email first."
                raise forms.ValidationError(msg, code="email_not_verified")
        except User.DoesNotExist as e:
            msg = "User does not exist."
            raise forms.ValidationError(msg, code="user_does_not_exist") from e

        self.cleaned_data["user"] = user
        return email


class SignInWithEmailForm(BaseEmailForm):
    def clean_email(self):
        super().clean_email()

        user = self.cleaned_data.get("user")
        if not user.login_with_email:
            msg = "Please enable login with email."
            raise forms.ValidationError(msg, code="login_with_email_disabled")

        return self.cleaned_data.get("email")


class ForgotPasswordForm(BaseEmailForm):
    pass


class ResetPasswordForm(BaseModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(),
        strip=False,
        required=True,
    )

    class Meta:
        model = User
        fields = ["password"]
        widgets = {
            "password": forms.PasswordInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            msg = "Passwords do not match."
            raise forms.ValidationError(msg, code="passwords_do_not_match")

        is_valid, message = validate_password(password, self.instance)
        if not is_valid:
            raise forms.ValidationError(message, code="invalid_password")

        return cleaned_data

    def save(self, commit=True):  # noqa: FBT002
        user = super().save(commit=False)
        user.set_password(user.password)
        if commit:
            user.save()
        return user
