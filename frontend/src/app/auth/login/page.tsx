'use client';

import React, { useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { Lock, Mail } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';

import { API_BASE_URL, TOKEN_KEY } from '@/lib/constants';
import { setCookie } from '@/lib/cookies';
import { loginSchema, type LoginFormData } from '@/lib/schemas/auth';
import { Organization } from '@/lib/types/organization';

export default function Login() {
  const router = useRouter();
  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const [isLoading, setIsLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(values: LoginFormData) {
    setIsLoading(true);
    setFormError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Login failed');
      }

      const data = await response.json();
      if (data.token) {
        setCookie(TOKEN_KEY, data.token);
      }
      if (data.sessionId) {
        setCookie('sessionId', data.sessionId);
        setCookie('expiry', data.expires_in);
      }
      const user = {
        ...data.user,
        roles: data.user.roles.map((role: Organization) => {
          return {
            role: role.role,
            permissions: role.permissions,
            organization_id: role.organization_id,
            organization_uid: role.organization_uid,
            organization_name: role.organization_name,
          };
        }),
      };
      setCookie('user', JSON.stringify(user));
      setCookie('organization', JSON.stringify(user.roles[0]));

      router.push('/dashboard');
    } catch (error) {
      console.error('Login error:', error);
      setFormError(
        error instanceof Error ? error.message : 'An unknown error occurred',
      );
    } finally {
      setIsLoading(false);
    }
    setIsLoading(false);
  }

  return (
    <section className="grid h-screen w-screen place-items-center bg-[url(/assets/jpeg/login-background.jpg)]">
      <div className="bg-background w-full max-w-lg rounded-lg p-10 shadow-md">
        <div className="mb-8 flex items-end justify-center">
          <Image
            src={'/assets/png/vyomos-logo.png'}
            alt="Vyom Fleet Management Logo"
            className="mr-2.5 h-[50px] w-[50px]"
            width={50}
            height={50}
          />
          <div>
            <div className="text-left font-sans text-[25px] leading-[25px] font-light">
              FLEET
            </div>
            <div className="text-left font-sans text-[25px] leading-[25px] font-light">
              MANAGEMENT
            </div>
          </div>
        </div>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col gap-5"
          >
            {formError && (
              <div className="-mt-2.5 mb-2.5 text-center text-sm text-red-600">
                {formError}
              </div>
            )}

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 transform text-gray-400" />
                      <Input
                        type="email"
                        placeholder="yours@example.com"
                        className="w-full rounded border border-gray-300 px-10 py-5 text-sm transition-colors duration-200 outline-none focus:border-blue-700 focus:ring-0"
                        {...field}
                        aria-label="Email Address"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <div className="relative">
                      <Lock className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 transform text-gray-400" />
                      <Input
                        type="password"
                        placeholder="password/otp"
                        className="w-full rounded border border-gray-300 px-10 py-5 text-sm transition-colors duration-200 outline-none focus:border-blue-700 focus:ring-0"
                        {...field}
                        aria-label="Password"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="-mt-2.5 text-right">
              <Link
                href="/forgot-password"
                className="text-sm text-gray-600 no-underline hover:text-blue-700"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full rounded bg-blue-700 py-6 text-base font-medium text-white transition-colors duration-200 hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-blue-200"
            >
              {isLoading ? 'Please wait...' : 'LOGIN'}
            </Button>
          </form>
        </Form>

        <div className="mt-5 text-center text-sm text-gray-600">
          Don&apos;t have an account?
          <Link
            href="/auth/register"
            className="ml-1.5 font-medium text-blue-700 no-underline hover:underline"
          >
            Sign Up
          </Link>
        </div>

        <div className="mt-5 flex justify-center gap-5">
          <Image
            src={'/assets/png/google-logo.png'}
            alt="Sign in with Google"
            className="h-6 w-6 cursor-pointer"
            width={24}
            height={24}
          />
          <Image
            src={'/assets/png/microsoft-logo.png'}
            alt="Sign in with Microsoft"
            className="h-6 w-6 cursor-pointer"
            width={24}
            height={24}
          />
        </div>
      </div>
    </section>
  );
}
