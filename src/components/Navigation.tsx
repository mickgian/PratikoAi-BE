'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from './ui/button'
import { Menu, X, Brain, Shield, FileText, HelpCircle } from 'lucide-react'

interface NavigationProps {
  onSignUpClick?: () => void
  onSignInClick?: () => void
}

export function Navigation({ onSignUpClick, onSignInClick }: NavigationProps) {
  const [isScrolled, setIsScrolled] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const menuItems = [
    { name: 'Funzionalità', href: '#features', icon: Brain },
    { name: 'Prezzi', href: '#pricing', icon: FileText },
    { name: 'Chi Siamo', href: '#about', icon: Shield },
    { name: 'FAQ', href: '#faq', icon: HelpCircle },
  ]

  const handleNavClick = (href: string) => {
    setIsMobileMenuOpen(false)
    // Small delay to allow mobile menu to close before scrolling
    setTimeout(() => {
      const element = document.querySelector(href)
      if (element) {
        const navHeight = 80 // Account for fixed navigation height
        const elementTop = element.getBoundingClientRect().top + window.pageYOffset - navHeight
        window.scrollTo({
          top: elementTop,
          behavior: 'smooth'
        })
      }
    }, 100)
  }

  return (
    <motion.nav
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-white/95 backdrop-blur-sm shadow-lg'
          : 'bg-white'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="flex items-center space-x-2"
          >
            <div className="w-8 h-8 bg-[#2A5D67] rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-[#2A5D67]">PratikoAI</span>
          </motion.div>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center space-x-8">
            {menuItems.map((item, index) => (
              <motion.a
                key={item.name}
                href={item.href}
                onClick={(e) => {
                  e.preventDefault()
                  handleNavClick(item.href)
                }}
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.3, delay: 0.3 + index * 0.05 }}
                className="group relative text-[#2A5D67] hover:text-[#1E293B] transition-all duration-200 font-medium cursor-pointer"
              >
                <span className="flex items-center space-x-1">
                  <item.icon className="w-4 h-4 opacity-70 group-hover:opacity-100 transition-opacity" />
                  <span>{item.name}</span>
                </span>
                <motion.div
                  className="absolute -bottom-1 left-0 h-0.5 bg-[#2A5D67] origin-left"
                  initial={{ scaleX: 0 }}
                  whileHover={{ scaleX: 1 }}
                  transition={{ duration: 0.2 }}
                />
              </motion.a>
            ))}
          </div>

          {/* Desktop CTA Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            <motion.div
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.6 }}
            >
              <Button
                onClick={onSignInClick}
                variant="ghost"
                className="text-[#2A5D67] border border-[#2A5D67] hover:bg-[#F8F5F1] transition-all duration-200"
              >
                Accedi
              </Button>
            </motion.div>
            <motion.div
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.7 }}
            >
              <Button
                onClick={onSignUpClick}
                className="bg-[#2A5D67] hover:bg-[#1E293B] transition-all duration-300 shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <span className="text-[#D4A574] font-bold">Prova Gratuita</span>
              </Button>
            </motion.div>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="text-[#2A5D67] hover:bg-[#F8F5F1]"
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="md:hidden bg-white border-t border-[#C4BDB4]/30"
          >
            <div className="px-4 py-6 space-y-4">
              {menuItems.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  className="flex items-center space-x-2 text-[#2A5D67] hover:text-[#1E293B] transition-colors cursor-pointer"
                  onClick={(e) => {
                    e.preventDefault()
                    handleNavClick(item.href)
                  }}
                >
                  <item.icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </a>
              ))}
              <div className="pt-4 space-y-2">
                <Button
                  onClick={onSignInClick}
                  variant="outline"
                  className="w-full text-[#2A5D67] border-[#2A5D67] hover:bg-[#F8F5F1]"
                >
                  Accedi
                </Button>
                <Button onClick={onSignUpClick} className="w-full bg-[#2A5D67] hover:bg-[#1E293B]">
                  <span className="text-[#D4A574] font-bold">Prova Gratuita</span>
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </motion.nav>
  )
}