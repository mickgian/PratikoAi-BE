import { ChatLayout } from './components/ChatLayout'
import { ChatStateProvider } from './hooks/useChatState'
import { ChatSessionsProvider } from './hooks/useChatSessions'

export default function ChatPage() {
  // Uncomment the line below to see the message display demo
  // return <MessageDisplayDemo />
  
  return (
    <ChatStateProvider>
      <ChatSessionsProvider>
        <ChatLayout />
      </ChatSessionsProvider>
    </ChatStateProvider>
  )
}