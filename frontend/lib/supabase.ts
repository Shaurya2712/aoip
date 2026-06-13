// STATUS: COMPLETE
import { createClientComponentClient, createServerComponentClient } from '@supabase/auth-helpers-nextjs'

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'https://placeholder.supabase.co'
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? 'placeholder-anon-key'

export const createClient = () =>
  createClientComponentClient({
    supabaseUrl,
    supabaseKey: supabaseAnonKey,
  })

export const createServerClient = () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { cookies } = require('next/headers')
  return createServerComponentClient(
    { cookies },
    {
      supabaseUrl,
      supabaseKey: supabaseAnonKey,
    }
  )
}
