import { useEffect } from 'react';
import { useRouter } from 'next/router';
import ProjectUploadPage from '../DrawingUpload';

export default function DrawingsPage() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  return <ProjectUploadPage />;
} 