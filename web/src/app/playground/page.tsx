import type { Metadata } from "next";
import { Playground } from "@/components/playground/Playground";

export const metadata: Metadata = {
  title: "Playground",
  description: "Escribe un archivo .dscops, valídalo y compílalo desde el navegador.",
};

export default function PlaygroundPage() {
  return <Playground />;
}
