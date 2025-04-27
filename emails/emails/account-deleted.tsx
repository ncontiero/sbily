import { Heading, Section } from "@react-email/components";
import { Button } from "../components/button";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { NotRequested } from "../components/not-requested";
import { Text } from "../components/text";

export default function AccountDeleted() {
  const title = "Account Deleted";
  const text =
    "Your account has been successfully deleted. If you didn't make this change, please contact support immediately.";

  return (
    <Layout title={title} previewText={text}>
      <Card className="rounded-[10px] border-l-4 border-solid border-destructive py-[10px]">
        <Heading as="h3" className="font-semibold text-destructive">
          Account Permanently Deleted
        </Heading>
        <Text>
          This is an automatic notification to inform you that your Sbily
          account has been permanently deleted as requested.
        </Text>
      </Card>
      <Section className="text-center">
        <Text className="mb-[6px] mt-[26px]">User account:</Text>
        <Card className="mt-0 w-fit p-[6px]">{`{{ username }}`}</Card>
      </Section>
      <Card variant="outline" className="mt-[32px] py-0">
        <Heading as="h3" className="text-[18px] font-semibold">
          What happens to your data?
        </Heading>
        <Text>
          All your personal information, links, and related data have been
          permanently removed from our systems in accordance with our privacy
          policy.
        </Text>
      </Card>
      <Card variant="outline" className="py-0">
        <Heading as="h3" className="text-[18px] font-semibold">
          What if you change your mind?
        </Heading>
        <Text>
          This action is irreversible. If you wish to use Sbily again in the
          future, you'll need to create a new account.
        </Text>
      </Card>
      <Section className="mb-[24px] mt-[32px] text-center">
        <Text>
          We're sorry to see you go. If you'd like to share why you decided to
          delete your account, we'd appreciate your feedback.
        </Text>
        <Button variant="outline" href="{{ BASE_URL }}">
          Share Feedback
        </Button>
      </Section>
      <NotRequested text="If you did not request this account deletion, please contact us immediately by replying to this email or reaching out to an administrator for support." />
    </Layout>
  );
}
