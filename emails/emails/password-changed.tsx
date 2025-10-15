import { Heading, Section } from "@react-email/components";
import { Button } from "../components/button";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { NotRequested } from "../components/not-requested";
import { Text } from "../components/text";

const recommendations = [
  "Make sure to keep your new password in a secure place and don't share it with anyone.",
  "Consider updating passwords on other sites if you were using the same password elsewhere.",
];

export default function PasswordChanged() {
  const title = "Password Changed";
  const text =
    "Your password has been successfully changed. If you didn't make this change, please contact support immediately.";
  const time = "{{ now }}";

  return (
    <Layout title={title} previewText={text}>
      <Card className="rounded-[10px] border-l-4 border-solid border-primary py-[10px]">
        <Heading as="h3" className="font-semibold text-primary">
          Security Alert
        </Heading>
        <Text>
          This is an automatic notification to inform you that the password for
          account <span className="font-semibold">{`{{ user.email }}`}</span>{" "}
          has been successfully changed.
        </Text>
        <Text>The change was made on {time}.</Text>
      </Card>
      <Section>
        <Heading as="h3" className="mt-[32px] text-[18px] font-semibold">
          Security recommendations:
        </Heading>
        {recommendations.map((recommendation, index) => (
          <Text key={index} className="mt-[10px] inline-flex items-start">
            <span
              className={`
                mr-[12px] flex size-[18px] shrink-0 items-center justify-center rounded-[6px] border border-solid
                border-primary pl-[2px] text-[18px] font-semibold leading-none text-primary
              `}
            >
              ✓
            </span>
            {recommendation}
          </Text>
        ))}
      </Section>
      <Section className="text-center">
        <Text>If this was you, no further action is needed.</Text>
        <Button href={`{{ BASE_URL }}{% url "my_account" %}`}>
          Sign in to your account
        </Button>
      </Section>
      <NotRequested text="If you did not make this change, please contact us immediately by replying to this email or reaching out to an administrator for support." />
    </Layout>
  );
}
