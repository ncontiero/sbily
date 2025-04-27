import { Heading } from "@react-email/components";
import { Action } from "../components/action";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { NotRequested } from "../components/not-requested";
import { Text } from "../components/text";

export default function ChangeEmail() {
  const title = "Change Your Email";
  const text =
    "You've requested to change the email address associated with your Sbily account.";

  return (
    <Layout title={title} previewText={text}>
      <Text>
        You've requested to change the email address associated with your Sbily
        account.
      </Text>
      <Action
        text="Click the button below to continue with changing your email address:"
        buttonText="Change My Email"
        link="{{ change_email_link }}"
      />
      <Card variant="outline" className="py-0">
        <Heading as="h3" className="text-[18px] font-semibold">
          What happens next?
        </Heading>
        <Text>
          After clicking the button, you'll be asked to enter your new email
          address. Once submitted, a verification email will be sent to your new
          address to confirm the change.
        </Text>
      </Card>
      <NotRequested text="If you didn't make this request, you can safely ignore this email. Your email address will remain unchanged." />
    </Layout>
  );
}
