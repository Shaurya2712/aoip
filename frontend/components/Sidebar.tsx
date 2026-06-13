// STATUS: COMPLETE
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  Activity,
  FileText,
  Layers,
  LayoutDashboard,
  LogOut,
  Search,
  Swords,
  Trophy,
  Users,
} from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const navItems = [
  { href: '/', label: 'Home', icon: LayoutDashboard },
  { href: '/opportunities', label: 'Opportunities', icon: Trophy },
  { href: '/keywords', label: 'Keywords', icon: Search },
  { href: '/competitors', label: 'Competitors', icon: Swords },
  { href: '/community', label: 'Community', icon: Users },
  { href: '/niches', label: 'Niches', icon: Layers },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/scheduler', label: 'Scheduler', icon: Activity },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const supabase = createClient()

  async function handleSignOut() {
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col bg-slate-900 text-white">
      <div className="border-b border-slate-700 px-6 py-5">
        <span className="text-xl font-bold tracking-wide">AOIP</span>
        <p className="mt-1 text-xs text-slate-400">App Opportunity Intelligence</p>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === '/'
              ? pathname === '/'
              : pathname.startsWith(href)

          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-slate-700 p-4">
        <Button
          variant="outline"
          className="w-full border-slate-600 bg-transparent text-slate-200 hover:bg-slate-800 hover:text-white"
          onClick={handleSignOut}
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </aside>
  )
}
