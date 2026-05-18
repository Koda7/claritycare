import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import type { PolicyDetail } from '../types'
import TreeNode from '../components/TreeNode'

export default function PolicyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [policy, setPolicy] = useState<PolicyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/policies/${id}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => {
        setPolicy(data)
        setLoading(false)
      })
      .catch(e => {
        setError(e.message)
        setLoading(false)
      })
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (error || !policy) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error loading policy: {error}</p>
        <Link to="/" className="text-indigo-600 hover:underline mt-4 inline-block">
          &larr; Back to list
        </Link>
      </div>
    )
  }

  return (
    <div>
      <Link
        to="/"
        className="inline-flex items-center text-sm text-gray-600 hover:text-indigo-600 mb-6"
      >
        &larr; Back to all policies
      </Link>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">
          {policy.structured_json?.title || policy.title}
        </h1>
        <div className="flex flex-wrap gap-4 text-sm text-gray-600">
          <a
            href={policy.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 hover:underline"
          >
            View PDF &rarr;
          </a>
          <a
            href={policy.source_page_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 hover:underline"
          >
            Source Page &rarr;
          </a>
          {policy.llm_model && (
            <span className="text-gray-500">Model: {policy.llm_model}</span>
          )}
          {policy.structured_at && (
            <span className="text-gray-500">
              Structured: {new Date(policy.structured_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      {policy.validation_error && !policy.structured_json && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <p className="text-sm font-medium text-red-800">Validation Error</p>
          <p className="text-sm text-red-700 mt-1 font-mono">{policy.validation_error}</p>
        </div>
      )}

      {policy.structured_json ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Criteria Decision Tree
            </h2>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {policy.structured_json.insurance_name}
            </span>
          </div>
          <TreeNode node={policy.structured_json.rules} depth={0} />
        </div>
      ) : (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No structured criteria available for this policy.</p>
        </div>
      )}
    </div>
  )
}
