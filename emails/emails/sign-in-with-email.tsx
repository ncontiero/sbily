import { Action } from "../components/action";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { NotRequested } from "../components/not-requested";
import { Text } from "../components/text";

export default function SignInWithEmail() {
  const title = "Sign in to Sbily";
  const text =
    "You requested to sign in to your Sbily account. Use the secure button below to access your account.";

  return (
    <Layout title={title} previewText={text}>
      <Text>{text}</Text>
      <Action
        text="Click the button below to sign in to your account:"
        buttonText="Sign In to My Account"
        link="{{ sign_in_with_email_link }}"
      />
      <Card variant="outline" className="border-primary py-0">
        <Text className="font-medium">
          For your security, this login link can only be used once and will
          expire in 30 minutes or so after use.
        </Text>
      </Card>
      <NotRequested text="If you didn't make this request, you can safely ignore this email. Someone might have entered your email address by mistake." />
    </Layout>
  );
}
