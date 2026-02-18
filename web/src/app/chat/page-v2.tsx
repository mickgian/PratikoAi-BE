/**
 * @file Chat Page V2 with Hybrid Storage
 * @description Enhanced chat page with PostgreSQL + IndexedDB hybrid storage
 * Phase 3 implementation of chat history migration
 */

import { ChatLayoutV2 } from './components/ChatLayoutV2';
import { ChatStateProvider } from './hooks/useChatState';
import { ChatSessionsProvider } from './hooks/useChatSessions';

/**
 * Chat Page Component V2
 *
 * **Phase 3 Enhancements:**
 * - Uses ChatLayoutV2 with migration banner support
 * - Hybrid storage (PostgreSQL primary, IndexedDB fallback)
 * - Automatic migration detection and user prompting
 * - Offline-first graceful degradation
 *
 * **Architecture:**
 * - ChatStateProvider: Global chat state management
 * - ChatSessionsProvider: Session list and switching
 * - ChatLayoutV2: UI with migration banner
 */
export default function ChatPageV2() {
  return (
    <ChatStateProvider>
      <ChatSessionsProvider>
        <ChatLayoutV2 />
      </ChatSessionsProvider>
    </ChatStateProvider>
  );
}
