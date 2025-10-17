import {
  type ButtonProps as ReactEmailButtonProps,
  Button as ReactEmailButton,
} from "@react-email/components";
import { cn } from "../utils/cn";

interface ButtonProps extends ReactEmailButtonProps {
  variant?: "primary" | "outline";
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <ReactEmailButton
      className={cn(
        "text-foreground rounded-[6px] px-[20px] py-[14px] text-center text-[16px]",
        variant === "primary" && "bg-primary text-primary-foreground",
        variant === "outline" &&
          "border-primary text-primary border border-solid",
        className,
      )}
      {...props}
    />
  );
}
