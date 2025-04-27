import { Heading, Hr, Section } from "@react-email/components";
import { Text } from "./text";

export function Header() {
  return (
    <Section className="text-center">
      <Heading className="my-[12px]">
        <span className="text-primary">Sb</span>
        <span>ily</span>
      </Heading>
      <Text className="mb-[24px]">
        A simple, fast, and secure Open-Source link shortener.
      </Text>
      <Hr />
    </Section>
  );
}
