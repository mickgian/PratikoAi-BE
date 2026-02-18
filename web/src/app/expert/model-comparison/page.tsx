import { Suspense } from 'react';
import { ComparisonDashboard } from './components/ComparisonDashboard';

function DashboardLoading() {
  return (
    <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
      <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
    </div>
  );
}

export default function ModelComparisonPage() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <ComparisonDashboard />
    </Suspense>
  );
}
