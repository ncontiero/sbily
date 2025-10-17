import { Column, Heading, Row, Section } from "@react-email/components";
import { Button } from "../components/button";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { NotRequested } from "../components/not-requested";
import { Text } from "../components/text";

export default function EmailChanged() {
  const title = "Email Changed";
  const text =
    "Your email has been successfully changed. If you didn't make this change, please contact support immediately.";
  const time = "{{ now }}";

  return (
    <Layout title={title} previewText={text}>
      <Card className="border-primary rounded-[10px] border-l-4 border-solid py-[10px]">
        <Heading as="h3" className="text-primary font-semibold">
          Email Change Notification
        </Heading>
        <Text>
          This is an automated notification to inform you that the email address
          for account{" "}
          <span className="font-semibold">{`{{ user.username }}`}</span> has
          been changed.
        </Text>
        <Text>The change was made on {time}.</Text>
      </Card>
      <Card variant="outline">
        <Row cellSpacing={8} className="ml-0 w-full max-w-[364px] table-fixed">
          <Column className="w-[100px]">
            <Text className="text-muted-foreground m-0">Previous:</Text>
          </Column>
          <Column className="bg-secondary w-full rounded-[6px] px-[10px] py-[6px]">
            <Text className="text-foreground m-0">{`{{ old_email }}`}</Text>
          </Column>
        </Row>
        <Row cellSpacing={8} className="ml-0 w-full max-w-[364px] table-fixed">
          <Column className="w-[100px]">
            <Text className="text-muted-foreground m-0">New:</Text>
          </Column>
          <Column className="bg-secondary w-full rounded-[6px] px-[10px] py-[6px]">
            <Text className="text-foreground m-0">{`{{ user.email }}`}</Text>
          </Column>
        </Row>
      </Card>
      {`{% if not is_old %}`}
      <Section className="text-center">
        <Text className="mt-[32px]">
          To complete this process, please verify your new email address:
        </Text>
        <Button href={`{{ verify_email_link  }}`} className="my-[16px]">
          Verify New Email
        </Button>
        <Text className="text-muted-foreground text-[14px]">
          This verification link expires in 24 hours
        </Text>
      </Section>
      <NotRequested text="If you didn't make this request, you can safely ignore this email." />
      {`{% else %}`}
      <Text className="mb-0">
        All future notifications will be sent to your new email address once
        it's verified.
      </Text>
      <NotRequested text="If you didn't make this request, please contact us immediately by replying to this email or reaching out to an administrator for support." />
      {`{% endif %}`}
    </Layout>
  );
}
