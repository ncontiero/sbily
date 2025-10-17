import {
  type TextProps,
  Text as ReactEmailText,
} from "@react-email/components";
import { cn } from "../utils/cn";

export function Text({ className, ...props }: TextProps) {
  return (
    <ReactEmailText
      className={cn("text-foreground text-[16px] leading-[24px]", className)}
      {...props}
    />
  );
}
