import { Section } from "@react-email/components";
import { Button } from "./button";
import { Text } from "./text";

interface ActionProps {
  text: string;
  buttonText: string;
  link: string;
  expires?: string;
}

export function Action({
  text,
  buttonText,
  link,
  expires = "30 minutes",
}: ActionProps) {
  return (
    <>
      <Section className="mt-[20px] rounded-[6px] bg-secondary p-[20px] text-center">
        <Text>{text}</Text>
        <Button href={link} className="my-[16px]">
          {buttonText}
        </Button>
        <Text className="text-[14px] text-muted-foreground">
          Link expires in {expires}
        </Text>
      </Section>
      <Text className="mt-[26px]">
        Having trouble with the button? You can also copy and paste this URL
        into your browser:
      </Text>
      <Text
        className={`
          mt-[20px] rounded-[6px] border border-solid border-border bg-background p-[20px] text-muted-foreground
        `}
      >
        {link}
      </Text>
    </>
  );
}
