'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Cpu, BotIcon as Robot, Search } from 'lucide-react';
import Link from 'next/link';

export default function NotFound() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="flex h-full flex-col items-center justify-center bg-slate-900 p-4 text-white">
      <div className="w-full space-y-8 text-center">
        {/* Error Code with Glitch Effect */}
        <motion.div
          className="flex items-center justify-center gap-4 py-6"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="relative">
            {/* Base 404 text */}
            <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-7xl font-bold text-transparent select-none md:text-9xl">
              404
            </span>

            {/* Glitch layers */}
            <motion.span
              className="absolute inset-0 text-7xl font-bold text-red-500 opacity-70 select-none md:text-9xl"
              animate={{
                x: [0, -3, 5, -2, 0, 2, -5, 0],
                y: [0, 2, -1, 0, -2, 1, 0],
                opacity: [0.7, 0.3, 0.7, 0.5, 0.7],
              }}
              transition={{
                duration: 0.4,
                repeat: Number.POSITIVE_INFINITY,
                repeatType: 'reverse',
                ease: 'easeInOut',
                times: [0, 0.2, 0.3, 0.5, 0.6, 0.8, 0.9, 1],
              }}
              style={{ textShadow: '2px 0 #00fffc, -2px 0 #fc00ff' }}
            >
              404
            </motion.span>

            <motion.span
              className="absolute inset-0 text-7xl font-bold text-cyan-500 opacity-70 select-none md:text-9xl"
              animate={{
                x: [0, 3, -5, 2, 0, -2, 5, 0],
                y: [0, -2, 1, 0, 2, -1, 0],
                opacity: [0.7, 0.5, 0.7, 0.3, 0.7],
              }}
              transition={{
                duration: 0.3,
                repeat: Number.POSITIVE_INFINITY,
                repeatType: 'reverse',
                ease: 'easeInOut',
                times: [0, 0.1, 0.3, 0.4, 0.6, 0.8, 0.9, 1],
              }}
              style={{ textShadow: '-2px 0 #00fffc, 2px 0 #fc00ff' }}
            >
              404
            </motion.span>

            {/* Random glitch flickers */}
            {[...Array(3)].map((_, i) => (
              <motion.span
                key={i}
                className="absolute inset-0 text-7xl font-bold text-white opacity-0 select-none md:text-9xl"
                animate={{
                  opacity: [0, 0.9, 0],
                  x: [0, i % 2 === 0 ? 5 : -5, 0],
                }}
                transition={{
                  duration: 0.2,
                  repeat: Number.POSITIVE_INFINITY,
                  repeatDelay: Math.random() * 5 + 2,
                  ease: 'easeInOut',
                }}
                style={{
                  clipPath: `polygon(${
                    Math.random() * 100
                  }% 0%, 100% 0%, 100% ${Math.random() * 100}%, 0% 100%)`,
                  filter: 'brightness(2)',
                }}
              >
                404
              </motion.span>
            ))}

            {/* Digital noise lines */}
            <motion.div
              className="pointer-events-none absolute inset-0 overflow-hidden opacity-30"
              animate={{ opacity: [0.3, 0.5, 0.3] }}
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            >
              {[...Array(5)].map((_, i) => (
                <motion.div
                  key={i}
                  className="bg-background absolute h-[1px] w-full"
                  initial={{ y: Math.random() * 100 + '%', scaleX: 0, left: 0 }}
                  animate={{
                    y: [
                      `${Math.random() * 100}%`,
                      `${Math.random() * 100}%`,
                      `${Math.random() * 100}%`,
                    ],
                    scaleX: [0, 1, 0],
                    left: ['0%', '100%', '0%'],
                  }}
                  transition={{
                    duration: 0.4,
                    repeat: Number.POSITIVE_INFINITY,
                    repeatDelay: Math.random() * 4,
                    ease: 'easeInOut',
                  }}
                />
              ))}
            </motion.div>
          </div>
        </motion.div>

        {/* Robot with search animation */}
        <motion.div
          className="relative flex justify-center py-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <motion.div
            animate={{
              x: [-20, 20, -20],
              rotateZ: [-5, 5, -5],
            }}
            transition={{
              duration: 4,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'easeInOut',
            }}
          >
            <Robot className="h-24 w-24 text-cyan-400" />
          </motion.div>

          <motion.div
            className="absolute top-0 right-1/3"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.7, 1, 0.7],
            }}
            transition={{
              duration: 2,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'easeInOut',
            }}
          >
            <Search className="h-10 w-10 text-blue-300" />
          </motion.div>
        </motion.div>

        {/* Title */}
        <motion.h1
          className="text-3xl font-bold md:text-5xl"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.7 }}
        >
          <span className="text-red-400">Error:</span> Page Not Found
        </motion.h1>

        {/* Subtitle */}
        <motion.div
          className="space-y-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.7 }}
        >
          <p className="text-xl text-slate-300">
            Our robots couldn&apos;t locate the requested file in the system.
          </p>
          <div className="flex items-center justify-center gap-2 text-amber-400">
            <AlertTriangle className="h-5 w-5" />
            <span className="font-mono">System Error: Resource_Not_Found</span>
          </div>
        </motion.div>

        {/* Return home button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.7 }}
        >
          <Link
            href="/"
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-6 py-3 font-medium transition-colors hover:from-cyan-600 hover:to-blue-700"
          >
            <Cpu className="h-4 w-4" />
            Return to Main System
          </Link>
        </motion.div>

        {/* Animated gears */}
        {/* <div className="flex justify-center gap-8 py-8">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{
              duration: 10,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'linear',
            }}
          >
            <Cog className="h-12 w-12 text-slate-500" />
          </motion.div>

          <motion.div
            animate={{ rotate: -360 }}
            transition={{
              duration: 15,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'linear',
            }}
          >
            <Cog className="h-16 w-16 text-slate-400" />
          </motion.div>
        </div> */}

        {/* Circuit board decoration */}
        <div className="relative mt-8 h-16">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-slate-600 to-transparent"></div>
          </div>
          <div className="absolute inset-0 flex items-center justify-around">
            {[...Array(8)].map((_, i) => (
              <motion.div
                key={i}
                className="h-3 w-3 rounded-full bg-red-500"
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
      </div>
    </div>
  );
}
