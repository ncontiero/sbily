import { Column, Heading, Row, Section } from "@react-email/components";
import { Action } from "../components/action";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { NotRequested } from "../components/not-requested";
import { Text } from "../components/text";

const questions = [
  {
    question: "Why do I need to verify my email?",
    answer:
      "Email verification helps us ensure your account security and prevents unauthorized access.",
  },
  {
    question: "What happens after verification?",
    answer:
      "Once verified, you'll have full access to all Sbily features including link management and analytics.",
  },
];

export default function VerifyEmail() {
  const title = "Verify your email address";
  const text =
    "We need to verify your email address to activate your Sbily account and unlock all features.";

  return (
    <Layout title={title} previewText={text}>
      <Text>{text}</Text>
      <Action
        text="Please click the button below to verify your email address:"
        buttonText="Verify My Email"
        link="{{ verify_email_link }}"
      />
      <Section>
        <Heading as="h3" className="mb-0 mt-[32px] text-[20px] font-semibold">
          Frequently Asked Questions
        </Heading>
        <Section>
          {questions.map((question, index) => (
            <Card key={index} as={Row} variant="outline">
              <Column>
                <Heading as="h4" className="m-0 text-[18px] font-semibold">
                  {question.question}
                </Heading>
                <Text className="mb-0 text-muted-foreground">
                  {question.answer}
                </Text>
              </Column>
            </Card>
          ))}
        </Section>
      </Section>
      <NotRequested text="If you didn't create an account with Sbily, you can safely ignore this email. It's possible someone entered your email address by mistake." />
    </Layout>
  );
}
