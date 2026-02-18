'use client'

import React, { useState } from 'react'
import { Navigation } from '../components/Navigation'
import { HeroSection } from '../components/HeroSection'
import { SocialProofBar } from '../components/SocialProofBar'
import { ProblemSolutionSection } from '../components/ProblemSolutionSection'
import { FeatureShowcase } from '../components/FeatureShowcase'
import { PricingSection } from '../components/PricingSection'
import { ChatInterface } from '../components/ChatInterface'
import { Footer } from '../components/Footer'
import { FAQSection } from '../components/FAQSection'

export default function Home() {
  const [isChatOpen, setIsChatOpen] = useState(false)

  const handleSignInClick = () => {
    window.location.href = '/signin'
  }

  const handleSignUpClick = () => {
    window.location.href = '/signup'
  }

  const handlePrivacyClick = () => {
    window.location.href = '/privacy-policy'
  }

  const handleTermsClick = () => {
    window.location.href = '/terms-of-service'
  }

  const handleCookiesClick = () => {
    window.location.href = '/cookie-policy'
  }

  const handleGDPRClick = () => {
    window.location.href = '/gdpr-compliance'
  }

  return (
    <div className="min-h-screen bg-white">
      <Navigation 
        onSignInClick={handleSignInClick}
        onSignUpClick={handleSignUpClick}
      />
      
      <main>
        <HeroSection />
        <SocialProofBar />
        <ProblemSolutionSection />
        <section id="features">
          <FeatureShowcase />
        </section>
        
        <PricingSection onSignUpClick={handleSignUpClick} />
        
        {/* Placeholder for About Section */}
        <section id="about" className="py-20 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold text-[#2A5D67] mb-4">
              Chi Siamo
            </h2>
            <p className="text-[#1E293B] text-lg mb-8">
              Il team di esperti dietro PratikoAI
            </p>
            <div className="bg-[#F8F5F1] rounded-lg p-8 shadow-sm max-w-2xl mx-auto">
              <p className="text-[#2A5D67] text-lg">
                Siamo un team di esperti in AI e normativa italiana, dedicati a supportare i professionisti nel loro lavoro quotidiano.
              </p>
            </div>
          </div>
        </section>

        <FAQSection />
      </main>
      
      <Footer 
        onNavigateToPrivacy={handlePrivacyClick}
        onNavigateToTerms={handleTermsClick}
        onNavigateToCookies={handleCookiesClick}
        onNavigateToGDPR={handleGDPRClick}
      />
      
      {/* Chat Interface */}
      <ChatInterface 
        isOpen={isChatOpen} 
        onToggle={() => setIsChatOpen(!isChatOpen)} 
      />
    </div>
  )
}