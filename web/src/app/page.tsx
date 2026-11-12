import { Hero } from "@/components/landing/Hero";
import { Language } from "@/components/landing/Language";
import { Pipeline } from "@/components/landing/Pipeline";
import { Rules } from "@/components/landing/Rules";
import { Targets } from "@/components/landing/Targets";
import { Footer } from "@/components/site/Footer";
import { Nav } from "@/components/site/Nav";

/** Página de inicio: qué es DSCOPS y cómo funciona. */
export default function HomePage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Language />
        <Pipeline />
        <Rules />
        <Targets />
      </main>
      <Footer />
    </>
  );
}
