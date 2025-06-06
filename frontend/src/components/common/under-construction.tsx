'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Cog, Cpu, Loader2, BotIcon as Robot } from 'lucide-react';

export default function UnderConstruction() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100 p-4 text-white">
      <div className="w-full max-w-3xl space-y-8 text-center">
        {/* Robot Icon */}
        <motion.div
          className="flex justify-center"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Robot className="h-24 w-24 text-blue-900" />
        </motion.div>

        {/* Title */}
        <motion.h1
          className="bg-gradient-to-r from-blue-900 to-blue-600 bg-clip-text text-4xl font-bold text-transparent md:text-6xl"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.7 }}
        >
          Under Construction
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          className="text-xl text-gray-500 md:text-2xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.7 }}
        >
          Our team is working hard to build something amazing
        </motion.p>

        {/* Animated gears */}
        <div className="flex justify-center gap-8 py-8">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{
              duration: 10,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'linear',
            }}
          >
            <Cog className="h-16 w-16 text-gray-500" />
          </motion.div>

          <motion.div
            animate={{ rotate: -360 }}
            transition={{
              duration: 15,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'linear',
            }}
          >
            <Cog className="h-24 w-24 text-gray-600" />
          </motion.div>

          <motion.div
            animate={{ rotate: 360 }}
            transition={{
              duration: 8,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'linear',
            }}
          >
            <Cog className="h-12 w-12 text-gray-400" />
          </motion.div>
        </div>

        {/* Status indicator */}
        <motion.div
          className="flex items-center justify-center gap-2 text-gray-600"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.7 }}
        >
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>System initialization: 37%</span>
        </motion.div>

        {/* Circuit board decoration */}
        <div className="relative mt-12 h-16">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-gray-600 to-transparent"></div>
          </div>
          <div className="absolute inset-0 flex items-center justify-around">
            {[...Array(8)].map((_, i) => (
              <motion.div
                key={i}
                className="h-3 w-3 rounded-full bg-blue-600"
                initial={{ opacity: 0.3 }}
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{
                  duration: 2,
                  repeat: Number.POSITIVE_INFINITY,
                  delay: i * 0.2,
                  ease: 'easeInOut',
                }}
              />
            ))}
          </div>
        </div>

        {/* CPU decoration */}
        <motion.div
          className="mt-8 flex justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.7 }}
        >
          <Cpu className="h-12 w-12 text-gray-600" />
        </motion.div>
      </div>
    </div>
  );
}
