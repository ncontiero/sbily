import { Hr, Section } from "@react-email/components";
import { Text } from "./text";

export function NotRequested({ text }: { text: string }) {
  return (
    <Section>
      <Hr className="mb-[20px] mt-[36px]" />
      <Text className="mb-[6px] font-medium">Didn't request this?</Text>
      <Text className="my-0 text-[14px] text-muted-foreground">{text}</Text>
    </Section>
  );
}
