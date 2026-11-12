"use client";

import { motion, type HTMLMotionProps } from "motion/react";
import Link from "next/link";
import type { ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

const VARIANT: Record<Variant, string> = {
  // Ámbar: la única acción principal de cada pantalla.
  primary: "bg-amber text-ink-deep hover:bg-[#f7c25c] shadow-[0_8px_24px_-10px_rgb(242_179_61/0.7)]",
  secondary: "border border-line bg-ink-deep/70 text-paper hover:border-pencil",
  ghost: "text-pencil hover:text-paper hover:bg-ink-soft",
};

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";

interface ButtonProps extends HTMLMotionProps<"button"> {
  variant?: Variant;
  children: ReactNode;
}

/** Botón con una pequeña respuesta al pulsar. */
export function Button({ variant = "secondary", className = "", children, ...props }: ButtonProps) {
  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.97 }}
      className={`${BASE} ${VARIANT[variant]} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}

interface LinkButtonProps {
  href: string;
  variant?: Variant;
  external?: boolean;
  className?: string;
  children: ReactNode;
}

export function LinkButton({ href, variant = "secondary", external, className = "", children }: LinkButtonProps) {
  const classes = `${BASE} ${VARIANT[variant]} ${className}`;
  if (external) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={classes}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={classes}>
      {children}
    </Link>
  );
}
