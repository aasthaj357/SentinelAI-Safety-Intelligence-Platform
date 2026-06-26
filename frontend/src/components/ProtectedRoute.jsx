import { Navigate } from 'react-router-dom';
import { useActiveProject } from '../context/ActiveProjectContext';

export default function ProtectedRoute({ session, children }) {
  const { isLoading } = useActiveProject();

  // While context is initializing, show a spinner instead of redirecting
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading your workspace...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/auth" replace />;
  }

  return children;
}
