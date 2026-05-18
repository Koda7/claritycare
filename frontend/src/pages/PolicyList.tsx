import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import type { PolicySummary, Stats } from '../types'

export default function PolicyList() {
  const [policies, setPolicies] = useState<PolicySummary[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'structured' | 'unstructured'>('all')

  useEffect(() => {
    Promise.all([
      fetch('/api/policies').then(r => r.json()),
      fetch('/api/stats').then(r => r.json()),
    ]).then(([policiesData, statsData]) => {
      setPolicies(policiesData)
      setStats(statsData)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const filtered = policies.filter(p => {
    if (filter === 'structured') return p.has_structured_data
    if (filter === 'unstructured') return !p.has_structured_data
    return true
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Policies Discovered" value={stats.total_policies} />
          <StatCard label="PDFs Downloaded" value={stats.downloaded} />
          <StatCard label="Successfully Structured" value={stats.structured} color="green" />
          <StatCard label="Failed Structuring" value={stats.failed_structuring} color="red" />
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Medical Guidelines ({filtered.length})
          </h2>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {(['all', 'structured', 'unstructured'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  filter === f
                    ? 'bg-white shadow-sm text-gray-900 font-medium'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {filtered.map(policy => (
            <div
              key={policy.id}
              className="px-6 py-4 hover:bg-gray-50 transition-colors flex items-center justify-between"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  {policy.has_structured_data ? (
                    <Link
                      to={`/policy/${policy.id}`}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-800 truncate"
                    >
                      {policy.title}
                    </Link>
                  ) : (
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {policy.title}
                    </span>
                  )}
                  {policy.has_structured_data && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Structured
                    </span>
                  )}
                  {policy.download_status === 200 && !policy.has_structured_data && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                      Downloaded
                    </span>
                  )}
                  {policy.download_status && policy.download_status !== 200 && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                      Failed
                    </span>
                  )}
                </div>
              </div>
              <a
                href={policy.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-4 text-xs text-gray-500 hover:text-indigo-600 shrink-0"
              >
                PDF &rarr;
              </a>
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="px-6 py-12 text-center text-gray-500">
            No policies found for this filter.
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  const colorClasses: Record<string, string> = {
    green: 'text-green-700',
    red: 'text-red-700',
    default: 'text-gray-900',
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-sm text-gray-600">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${colorClasses[color || 'default']}`}>
        {value}
      </p>
    </div>
  )
}
