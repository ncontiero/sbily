import { Action } from "../components/action";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { NotRequested } from "../components/not-requested";
import { Text } from "../components/text";

export default function ResetPasswordEmail() {
  const title = "Reset Your Password";
  const text =
    "We received a request to reset the password for your Sbily account. If you didn't make this request, you can safely ignore this email.";

  return (
    <Layout title={title} previewText={text}>
      <Text>{text}</Text>
      <Action
        text="To reset your password, click the button below:"
        buttonText="Reset My Password"
        link="{{ reset_password_link }}"
      />
      <Card className="border-primary py-0" variant="outline">
        <Text className="text-[18px] font-semibold">Security Reminder</Text>
        <Text>
          For better security, please create a strong password that you don't
          use on other websites. We recommend using a combination of uppercase
          letters, lowercase letters, numbers, and special characters.
        </Text>
      </Card>
      <NotRequested text="If you didn't request a password reset, you can safely ignore this email. Someone might have entered your email address by mistake." />
    </Layout>
  );
}
