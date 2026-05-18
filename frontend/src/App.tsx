import { Routes, Route, Link } from 'react-router-dom'
import PolicyList from './pages/PolicyList'
import PolicyDetailPage from './pages/PolicyDetail'

function App() {
  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">O</span>
              </div>
              <h1 className="text-xl font-semibold text-gray-900">
                Oscar Guidelines Explorer
              </h1>
            </Link>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<PolicyList />} />
          <Route path="/policy/:id" element={<PolicyDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
