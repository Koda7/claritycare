import { useState } from 'react'
import type { RuleNode } from '../types'

interface TreeNodeProps {
  node: RuleNode
  depth: number
}

export default function TreeNode({ node, depth }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2)
  const isLeaf = !node.rules || node.rules.length === 0
  const hasChildren = !isLeaf

  return (
    <div className={`${depth > 0 ? 'ml-6 border-l-2 border-gray-200 pl-4' : ''}`}>
      <div
        className={`flex items-start gap-2 py-2 ${hasChildren ? 'cursor-pointer' : ''}`}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren && (
          <button className="mt-0.5 shrink-0 w-5 h-5 flex items-center justify-center rounded text-gray-500 hover:bg-gray-100">
            <svg
              className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        )}

        {!hasChildren && (
          <span className="mt-1 shrink-0 w-2 h-2 rounded-full bg-gray-400"></span>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2">
            {node.operator && (
              <span
                className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${
                  node.operator === 'AND'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-amber-100 text-amber-800'
                }`}
              >
                {node.operator}
              </span>
            )}
            <span className="text-sm text-gray-800 leading-relaxed">
              <span className="text-gray-400 font-mono text-xs mr-1.5">
                {node.rule_id}
              </span>
              {node.rule_text}
            </span>
          </div>
        </div>
      </div>

      {hasChildren && expanded && (
        <div className="mt-1">
          {node.rules!.map((child) => (
            <TreeNode key={child.rule_id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}
