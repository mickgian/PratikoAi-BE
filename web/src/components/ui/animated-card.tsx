"use client";

import React from "react";
import { motion, MotionProps, cubicBezier } from "framer-motion";
import { cn } from "./utils";

interface AnimatedCardProps extends MotionProps {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
  delay?: number;
  duration?: number;
}

export function AnimatedCard({
  children,
  className,
  hoverEffect = true,
  delay = 0,
  duration = 0.6,
  ...motionProps
}: AnimatedCardProps) {
  return (
    <motion.div
      className={cn(
        "bg-background-primary rounded-lg border border-border-light p-6 shadow-professional",
        className
      )}
      initial={{ opacity: 0, y: 50, scale: 0.95 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: "-50px" }}
      whileHover={
        hoverEffect
          ? {
              y: -8,
              scale: 1.02,
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
            }
          : undefined
      }
      transition={{
        duration,
        delay,
        ease: cubicBezier(0, 0, 0.2, 1),
        ...motionProps.transition
      }}
      style={{
        ...motionProps.style,
      }}
      {...motionProps}
    >
      {children}
    </motion.div>
  );
}

// Animated Section Container
interface AnimatedSectionProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

const sectionVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      duration: 0.6,
      staggerChildren: 0.1
    }
  }
};

export function AnimatedSection({ 
  children, 
  className,
  delay = 0 
}: AnimatedSectionProps) {
  return (
    <motion.div
      className={className}
      variants={sectionVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-100px" }}
      transition={{ delay }}
    >
      {children}
    </motion.div>
  );
}

// Animated Text Elements
export const AnimatedHeading = motion.h1;
export const AnimatedParagraph = motion.p;
export const AnimatedDiv = motion.div;

// Pre-configured animation variants
export const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: cubicBezier(0, 0, 0.2, 1) }
  }
};

export const slideInLeft = {
  hidden: { opacity: 0, x: -50 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.8, ease: cubicBezier(0, 0, 0.2, 1) }
  }
};

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.5, ease: cubicBezier(0, 0, 0.2, 1) }
  }
};

export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      duration: 0.6,
      staggerChildren: 0.1
    }
  }
};