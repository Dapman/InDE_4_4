import { useParams, useLocation } from 'react-router-dom';
import { ChatContainer } from '../components/coaching/ChatContainer';

export default function CoachingPage() {
  const { id } = useParams();
  const location = useLocation();

  // Get initial message from navigation state (from NewPursuitPage)
  const initialMessage = location.state?.initialMessage;

  return <ChatContainer pursuitId={id} initialMessage={initialMessage} />;
}
