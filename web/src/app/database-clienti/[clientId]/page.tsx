'use client';

import { useParams } from 'next/navigation';
import { ClientDetailView } from '../components/ClientDetailView';

export default function ClientDetailPage() {
  const params = useParams();
  const clientId = params.clientId as string;
  return <ClientDetailView clientId={clientId} />;
}
