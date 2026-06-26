import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn("Supabase credentials not found. Make sure .env is configured.");
}

export const supabase = createClient(supabaseUrl || "http://placeholder", supabaseAnonKey || "placeholder")
