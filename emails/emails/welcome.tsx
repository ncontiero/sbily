import { Column, Heading, Row, Section } from "@react-email/components";
import { Button } from "../components/button";
import { Card } from "../components/card";
import { Layout } from "../components/layout";
import { Text } from "../components/text";

const features = [
  {
    title: "Easy to use",
    description:
      "Shorten your links in seconds, without complications. Intuitive and easy-to-use interface.",
  },
  {
    title: "Temporary Links",
    description:
      "Create links that automatically expire after a period you determine.",
  },
  {
    title: "Open Source",
    description:
      "Open-Source project, transparent and secure. Contribute to the development on GitHub.",
  },
];

export default function WelcomeEmail() {
  const title = "Welcome to Sbily!";
  const text =
    "Hello {{ name }}, thank you for joining Sbily, your new solution for shortening and managing links!";

  return (
    <Layout title={title} previewText={text}>
      <Text>
        Thank you for joining Sbily, your new solution for shortening and
        managing links!
      </Text>
      <Card className="text-center">
        <Heading as="h3" className="m-0 text-[22px] font-semibold">
          Why choose Sbily?
        </Heading>
        <Section>
          {features.map((feature, index) => (
            <Card key={index} as={Row} variant="outline">
              <Column>
                <Heading as="h4" className="m-0 text-[18px] font-semibold">
                  {feature.title}
                </Heading>
                <Text className="text-muted-foreground">
                  {feature.description}
                </Text>
              </Column>
            </Card>
          ))}
        </Section>
      </Card>
      <Section className="my-[20px] text-center">
        <Heading as="h3" className="mt-[32px] text-[18px] font-medium">
          Start shortening your links now
        </Heading>
        <Text className="text-muted-foreground">
          Simple, fast, and hassle-free. Try Sbily today.
        </Text>
        <Section>
          <Row className="w-full max-w-[300px]">
            <Column>
              <Button href={`{{ BASE_URL }}{% url "my_account" %}`}>
                Go to Dashboard
              </Button>
            </Column>
            <Column>
              <Button
                variant="outline"
                href={`{{ BASE_URL }}{% url "plans" %}`}
              >
                See plans
              </Button>
            </Column>
          </Row>
        </Section>
      </Section>
    </Layout>
  );
}
