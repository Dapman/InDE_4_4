import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-0 text-center p-8">
      <div className="text-8xl font-bold inde-gradient-text mb-4">404</div>
      <div className="text-display-md text-zinc-300 mb-3">Page Not Found</div>
      <p className="text-body-md text-zinc-500 mb-8 max-w-md">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/">
        <Button className="bg-inde-600 hover:bg-inde-700 text-white">
          Return to Dashboard
        </Button>
      </Link>
    </div>
  );
}
