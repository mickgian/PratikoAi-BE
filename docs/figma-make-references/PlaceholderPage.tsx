"use client";

import React from "react";
import { motion } from "motion/react";
import { Brain } from "lucide-react";

export function PlaceholderPage() {
  return (
    <div className="min-h-screen bg-[#1E293B] flex items-center justify-center overflow-hidden relative">
      {/* Background animated particles */}
      <div className="absolute inset-0">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-[#D4A574]/20 rounded-full"
            initial={{
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight,
            }}
            animate={{
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight,
            }}
            transition={{
              duration: Math.random() * 10 + 10,
              repeat: Infinity,
              repeatType: "reverse",
              ease: "linear",
            }}
          />
        ))}
      </div>

      {/* Center content */}
      <div className="relative z-10 flex flex-col items-center justify-center space-y-8">
        {/* Pulsing brain logo */}
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.7, 1, 0.7],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="relative"
        >
          {/* Outer glow ring */}
          <motion.div
            animate={{
              scale: [1, 1.3, 1],
              opacity: [0.3, 0, 0.3],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            className="absolute inset-0 bg-[#D4A574] rounded-full blur-2xl"
          />

          {/* Brain icon */}
          <motion.div
            animate={{
              rotate: [0, 5, -5, 0],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            className="relative"
          >
            <Brain className="w-32 h-32 text-[#D4A574]" strokeWidth={1.5} />
          </motion.div>
        </motion.div>

        {/* Animated dots below */}
        <div className="flex space-x-2">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 bg-[#D4A574] rounded-full"
              animate={{
                y: [0, -10, 0],
                opacity: [0.5, 1, 0.5],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: i * 0.2,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      </div>

      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#2A5D67]/10 via-transparent to-[#2A5D67]/10 pointer-events-none" />
    </div>
  );
}
