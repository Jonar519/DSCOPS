"use client";

import { motion } from "motion/react";
import { GITHUB_URL } from "@/lib/catalog";
import { LinkButton } from "../ui/Button";
import { IconGithub, IconPlay } from "../ui/Icons";
import { CompileDemo } from "./CompileDemo";

const enter = (delay: number) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] as const },
});

export function Hero() {
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-14 px-5 pb-24 pt-16 lg:grid-cols-[1fr_minmax(0,500px)] lg:pt-24">
      <div className="max-w-xl">
        <motion.p {...enter(0)} className="mb-6 font-mono text-sm text-pencil">
          <span className="text-amber">$</span> dscops build app.dscops --target compose,k8s
        </motion.p>

        <motion.h1
          {...enter(0.08)}
          className="text-[clamp(2.5rem,5.6vw,4.4rem)] font-semibold leading-[1.02] tracking-[-0.035em] text-balance"
        >
          Escribe la infraestructura una vez. Compílala segura.
        </motion.h1>

        <motion.p {...enter(0.16)} className="mt-6 max-w-[34rem] text-lg leading-relaxed text-pencil">
          DSCOPS es un compilador para un lenguaje declarativo propio. Revisa la sintaxis, la semántica y diez
          reglas de seguridad, y después genera Docker Compose, Kubernetes, GitHub Actions y Terraform.
        </motion.p>

        <motion.div {...enter(0.24)} className="mt-9 flex flex-wrap gap-3">
          <LinkButton href="/playground" variant="primary" className="px-5 py-2.5">
            <IconPlay size={14} /> Probar en el playground
          </LinkButton>
          <LinkButton href={GITHUB_URL} external className="px-5 py-2.5">
            <IconGithub size={16} /> Ver el código
          </LinkButton>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
      >
        <CompileDemo />
      </motion.div>
    </section>
  );
}
