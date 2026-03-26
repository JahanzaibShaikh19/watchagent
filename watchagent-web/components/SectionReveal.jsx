"use client";

import { motion } from "framer-motion";

export default function SectionReveal({ children, className = "", delay = 0 }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 26 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.65, ease: [0.2, 0.65, 0.25, 1], delay }}
      className={className}
    >
      {children}
    </motion.section>
  );
}
