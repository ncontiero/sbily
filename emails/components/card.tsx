import type { ElementType } from "react";
import { type SectionProps, Section } from "@react-email/components";
import { cn } from "../utils/cn";

interface CardProps extends SectionProps {
  variant?: "default" | "outline";
  as?: ElementType;
}

export function Card({
  className,
  variant = "default",
  as,
  ...props
}: CardProps) {
  const Comp = as || Section;

  return (
    <Comp
      className={cn(
        "mt-[26px] mb-0 rounded-[6px] p-[20px]",
        variant === "default" && "bg-secondary",
        variant === "outline" &&
          "border-border bg-background border border-solid",
        className,
      )}
      {...props}
    />
  );
}
