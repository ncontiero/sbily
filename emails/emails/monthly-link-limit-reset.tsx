import { Heading, Section } from "@react-email/components";
import { Button } from "../components/button";
import { Layout } from "../components/layout";
import { Text } from "../components/text";

const features = [
  "Intuitive and easy-to-use interface.",
  "Detailed click statistics.",
  "Link customization (on specific plans).",
];

export default function MonthlyLinkLimitResetEmail() {
  const title = "Your Links Limit Has Been Reset!";
  const previewText =
    "Great news! Your monthly link limit has been reset. Start shortening now!";

  return (
    <Layout title={title} previewText={previewText}>
      <Text className="mb-[20px]">
        We have great news! Your monthly limit for creating links on Sbily has
        been reset. This means you can now shorten and share your favorite links
        without any restrictions.
      </Text>

      <Section className="mt-[14px]">
        <Heading as="h3" className="mb-[10px] text-[20px] font-semibold">
          What can you do now?
        </Heading>
        <Text className="mb-[10px]">
          Take the opportunity to shorten new links, monitor the statistics of
          your existing links and optimize your campaigns.
        </Text>

        <Text className="mb-[10px]">
          Remember that Sbily offers several tools to facilitate your link
          management:
        </Text>

        <Section>
          {features.map((feature, index) => (
            <Text
              key={index}
              className="my-[6px] inline-flex w-full items-start"
            >
              <span className="border-primary text-primary mr-[12px] flex size-[18px] shrink-0 items-center justify-center rounded-[6px] border border-solid pl-[2px] text-[18px] leading-none font-semibold">
                ✓
              </span>
              {feature}
            </Text>
          ))}
        </Section>
      </Section>

      <Section className="mt-[10px]">
        <Text>
          We are always working to improve your experience with Sbily. If you
          have any questions or suggestions, please do not hesitate to contact
          our support team.
        </Text>
      </Section>

      <Section className="my-[20px] text-center">
        <Button href={`{{ BASE_URL }}{% url "dashboard" %}`}>
          Go to Dashboard
        </Button>
      </Section>
    </Layout>
  );
}
