// STATUS: COMPLETE
'use client'

import { Line, LineChart, ResponsiveContainer } from 'recharts'

interface TrendSparklineProps {
  data: number[]
}

export default function TrendSparkline({ data }: TrendSparklineProps) {
  if (!data.length) {
    return <div className="h-10 w-[120px] rounded bg-slate-100" />
  }

  const chartData = data.map((value, index) => ({ index, value }))
  const first = data[0]
  const last = data[data.length - 1]
  const color = last > first ? '#16a34a' : last < first ? '#dc2626' : '#94a3b8'

  return (
    <div className="h-10 w-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
