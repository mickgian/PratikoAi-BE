import React from 'react'
import Image from 'next/image'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from './ui/button'
import { X, Check } from 'lucide-react'

interface GoogleAccount {
  id: string
  name: string
  email: string
  avatar: string
}

interface GoogleAccountSelectorProps {
  isOpen: boolean
  onClose: () => void
  onSelectAccount: (account: GoogleAccount) => void
}

const mockGoogleAccounts: GoogleAccount[] = [
  {
    id: '1',
    name: 'Marco Ferretti',
    email: 'marco.ferretti@studiolegale.it',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face'
  },
  {
    id: '2',
    name: 'Marco Ferretti',
    email: 'marco.ferretti@gmail.com',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face'
  },
  {
    id: '3',
    name: 'Elena Bianchi',
    email: 'elena.bianchi@consulente.it',
    avatar: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150&h=150&fit=crop&crop=face'
  }
]

export function GoogleAccountSelector({ isOpen, onClose, onSelectAccount }: GoogleAccountSelectorProps) {
  const handleAccountSelect = (account: GoogleAccount) => {
    onSelectAccount(account)
    onClose()
  }

  const handleUseAnotherAccount = () => {
    // In a real implementation, this would trigger the Google OAuth flow
    alert('Reindirizzamento a Google per autenticazione...')
    onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-[#C4BDB4]/20">
                <div className="flex items-center space-x-3">
                  <svg className="w-6 h-6" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <div>
                    <h3 className="text-xl font-semibold text-[#2A5D67]">Scegli un account</h3>
                    <p className="text-sm text-[#1E293B]">per continuare con PratikoAI</p>
                  </div>
                </div>
                <Button
                  onClick={onClose}
                  variant="ghost"
                  size="sm"
                  className="text-[#C4BDB4] hover:text-[#2A5D67] hover:bg-[#F8F5F1] rounded-full w-8 h-8 p-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>

              {/* Account List */}
              <div className="max-h-80 overflow-y-auto">
                {mockGoogleAccounts.map((account, index) => (
                  <motion.button
                    key={account.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => handleAccountSelect(account)}
                    className="w-full p-4 hover:bg-[#F8F5F1] transition-colors duration-200 flex items-center space-x-4 border-b border-[#C4BDB4]/10 last:border-b-0 group"
                  >
                    <div className="relative">
                      <Image
                        src={account.avatar}
                        alt={account.name}
                        width={48}
                        height={48}
                        className="w-12 h-12 rounded-full object-cover ring-2 ring-[#C4BDB4]/20"
                      />
                      {/* Google account indicator */}
                      <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-white rounded-full flex items-center justify-center shadow-sm border border-[#C4BDB4]/20">
                        <svg className="w-3 h-3" viewBox="0 0 24 24">
                          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                      </div>
                    </div>
                    <div className="flex-1 text-left">
                      <p className="font-medium text-[#2A5D67]">{account.name}</p>
                      <p className="text-sm text-[#1E293B]">{account.email}</p>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <Check className="w-5 h-5 text-[#2A5D67]" />
                    </div>
                  </motion.button>
                ))}
              </div>

              {/* Footer Actions */}
              <div className="p-4 border-t border-[#C4BDB4]/20 bg-[#F8F5F1]/50">
                <Button
                  onClick={handleUseAnotherAccount}
                  variant="outline"
                  className="w-full border-[#C4BDB4] text-[#2A5D67] hover:bg-white hover:border-[#2A5D67] transition-all duration-200"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Usa un altro account
                </Button>

                <div className="mt-3 text-center">
                  <p className="text-xs text-[#C4BDB4]">
                    Per creare un account, Google condividerà il tuo nome, indirizzo email e immagine del profilo con PratikoAI.
                  </p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}