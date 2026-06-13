// STATUS: COMPLETE
import Sidebar from '@/components/Sidebar'

export const dynamic = 'force-dynamic'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <main className="ml-60 min-h-screen bg-slate-50 p-8">{children}</main>
    </div>
  )
}
