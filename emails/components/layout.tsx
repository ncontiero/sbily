import type { PropsWithChildren } from "react";
import {
  type TailwindConfig,
  Body,
  Container,
  Font,
  Head,
  Heading,
  Html,
  Preview,
  Tailwind,
} from "@react-email/components";
import { Footer } from "./footer";
import { Header } from "./header";
import { Text } from "./text";

export interface LayoutProps extends PropsWithChildren {
  readonly previewText: string;
  readonly title?: string;
}

const tailwindTheme: TailwindConfig["theme"] = {
  extend: {
    colors: {
      border: "#e5e7eb",
      background: "#fff",
      foreground: "#121212",
      primary: {
        DEFAULT: "#7c3aed",
        foreground: "#f9fafb",
      },
      secondary: {
        DEFAULT: "#f3f4f6",
        foreground: "#121212",
      },
      muted: {
        DEFAULT: "#f5f5f5",
        foreground: "#666",
      },
      destructive: {
        DEFAULT: "#ef4444",
        foreground: "#f9fafb",
      },
    },
  },
};

export function Layout({ title, previewText, children }: LayoutProps) {
  const name = "{{ name }}";

  return (
    <Html>
      <Tailwind config={{ theme: tailwindTheme }}>
        <Head>
          <Font
            fontFamily="Geist"
            fallbackFontFamily="Helvetica"
            webFont={{
              url: "https://cdn.jsdelivr.net/npm/@fontsource/geist-sans@5.2.5/files/geist-sans-latin-400-normal.woff2",
              format: "woff2",
            }}
            fontWeight={400}
            fontStyle="normal"
          />

          <Font
            fontFamily="Geist"
            fallbackFontFamily="Helvetica"
            webFont={{
              url: "https://cdn.jsdelivr.net/npm/@fontsource/geist-sans@5.2.5/files/geist-sans-latin-500-normal.woff2",
              format: "woff2",
            }}
            fontWeight={500}
            fontStyle="normal"
          />

          <Font
            fontFamily="Geist"
            fallbackFontFamily="Helvetica"
            webFont={{
              url: "https://cdn.jsdelivr.net/npm/@fontsource/geist-sans@5.2.5/files/geist-sans-latin-600-normal.woff2",
              format: "woff2",
            }}
            fontWeight={600}
            fontStyle="normal"
          />
        </Head>
        <Preview>{previewText}</Preview>

        <Body className="m-auto bg-background font-sans">
          <Container
            className={`
              mx-auto my-[40px] max-w-[600px] rounded-[6px] border border-solid border-transparent p-[20px]
              md:border-border
            `}
          >
            <Header />

            {title ? (
              <Heading
                as="h2"
                className="my-[20px] text-center text-[26px] font-semibold text-foreground"
              >
                {title}
              </Heading>
            ) : null}

            <Text>Hello {name}!</Text>
            {children}

            <br />
            <Footer />
          </Container>
        </Body>
      </Tailwind>
    </Html>
  );
}
