'use client';

import React from 'react';
import { motion } from 'motion/react';
import { Button } from './ui/button';
import { Check, Star, Zap } from 'lucide-react';
import { useBillingPlans } from '@/lib/hooks/useBillingPlans';

interface PricingSectionProps {
  onSignUpClick?: () => void;
}

const featuresByPlan: Record<string, string[]> = {
  base: [
    'Uso occasionale',
    'Accesso a tutte le funzionalità',
    'Supporto via email',
  ],
  pro: [
    'Uso quotidiano',
    'Accesso a tutte le funzionalità',
    'Supporto prioritario',
    'Limiti di utilizzo aumentati',
  ],
  premium: [
    'Uso intensivo',
    'Accesso a tutte le funzionalità',
    'Supporto dedicato',
    'Limiti di utilizzo massimi',
  ],
};

const descriptionByPlan: Record<string, string> = {
  base: 'Perfetto per iniziare e testare tutte le funzionalità',
  pro: 'Il piano ideale per professionisti che usano PratikoAI quotidianamente',
  premium: 'Per studi e team che necessitano di utilizzo intensivo',
};

function PricingCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl p-8 shadow-lg border-2 border-[#C4BDB4]/20 animate-pulse">
      <div className="text-center mb-8">
        <div className="h-7 bg-gray-200 rounded w-24 mx-auto mb-2" />
        <div className="h-4 bg-gray-200 rounded w-48 mx-auto mb-6" />
        <div className="h-12 bg-gray-200 rounded w-32 mx-auto mb-4" />
      </div>
      <div className="space-y-4 mb-8">
        {[1, 2, 3].map(i => (
          <div key={i} className="flex items-center space-x-3">
            <div className="w-5 h-5 bg-gray-200 rounded-full flex-shrink-0" />
            <div className="h-4 bg-gray-200 rounded w-full" />
          </div>
        ))}
      </div>
      <div className="h-12 bg-gray-200 rounded-xl w-full" />
    </div>
  );
}

export function PricingSection({ onSignUpClick }: PricingSectionProps) {
  const { plans, loading } = useBillingPlans();

  return (
    <section id="pricing" className="py-20 bg-[#F8F5F1]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <h2 className="text-4xl font-bold text-[#2A5D67] mb-4">
            Piani e Prezzi
          </h2>
          <p className="text-xl text-[#1E293B] max-w-3xl mx-auto">
            Scegli il piano più adatto alle tue esigenze professionali. Paghi in
            base all&apos;utilizzo con limiti chiari e trasparenti.
          </p>
        </motion.div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {loading
            ? [1, 2, 3].map(i => <PricingCardSkeleton key={i} />)
            : plans.map((plan, index) => {
                const isPopular = plan.slug === 'pro';
                const features = featuresByPlan[plan.slug] ?? [];
                const description = descriptionByPlan[plan.slug] ?? '';

                return (
                  <motion.div
                    key={plan.slug}
                    initial={{ opacity: 0, y: 50 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: index * 0.2 }}
                    whileHover={{ y: -10 }}
                    className={`relative bg-white rounded-2xl p-8 shadow-lg border-2 transition-all duration-300 ${
                      isPopular
                        ? 'border-[#D4A574] shadow-2xl'
                        : 'border-[#C4BDB4]/20 hover:border-[#D4A574]/50'
                    }`}
                  >
                    {/* Popular Badge */}
                    {isPopular && (
                      <motion.div
                        initial={{ scale: 0, opacity: 0 }}
                        whileInView={{ scale: 1, opacity: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.5 }}
                        className="absolute -top-4 left-1/2 transform -translate-x-1/2"
                      >
                        <div className="bg-[#D4A574] text-white px-6 py-2 rounded-full shadow-lg flex items-center space-x-2">
                          <Star className="w-4 h-4 fill-current" />
                          <span className="text-sm font-bold">POPOLARE</span>
                        </div>
                      </motion.div>
                    )}

                    {/* Plan Header */}
                    <div className="text-center mb-8">
                      <h3 className="text-2xl font-bold text-[#2A5D67] mb-2">
                        {plan.name}
                      </h3>
                      <p className="text-[#1E293B] mb-6 text-sm">
                        {description}
                      </p>

                      {/* Price */}
                      <div className="mb-4">
                        <div className="flex items-baseline justify-center space-x-2">
                          <span className="text-5xl font-bold text-[#2A5D67]">
                            &euro;{Math.round(plan.price_eur_monthly)}
                          </span>
                          <span className="text-xl text-[#1E293B]">/mese</span>
                        </div>
                      </div>
                    </div>

                    {/* Features List */}
                    <div className="space-y-4 mb-8">
                      {features.map((feature, featureIndex) => (
                        <motion.div
                          key={featureIndex}
                          initial={{ opacity: 0, x: -20 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          viewport={{ once: true }}
                          transition={{ delay: 0.3 + featureIndex * 0.1 }}
                          className="flex items-start space-x-3"
                        >
                          <Check className="w-5 h-5 text-[#2A5D67] mt-0.5 flex-shrink-0" />
                          <span className="text-[#1E293B] text-sm">
                            {feature}
                          </span>
                        </motion.div>
                      ))}
                    </div>

                    {/* CTA Button */}
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <Button
                        size="lg"
                        onClick={onSignUpClick}
                        className={`w-full h-auto py-4 rounded-xl transition-all duration-300 group ${
                          isPopular
                            ? 'bg-[#2A5D67] hover:bg-[#1E293B] text-white shadow-xl'
                            : 'bg-white border-2 border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white'
                        }`}
                      >
                        <motion.div
                          className="flex items-center space-x-2"
                          whileHover={{ x: 5 }}
                          transition={{ duration: 0.2 }}
                        >
                          <Zap className="w-5 h-5" />
                          <span className="font-bold">Inizia Ora</span>
                        </motion.div>
                      </Button>
                    </motion.div>

                    {/* Background Decoration */}
                    <div
                      className={`absolute top-0 right-0 w-32 h-32 opacity-5 transform rotate-12 translate-x-8 -translate-y-8 ${
                        isPopular ? 'text-[#D4A574]' : 'text-[#2A5D67]'
                      }`}
                    >
                      <Zap className="w-full h-full" />
                    </div>
                  </motion.div>
                );
              })}
        </div>

        {/* Additional Info */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="text-center mt-16"
        >
          <div className="bg-white rounded-lg p-8 shadow-sm border border-[#C4BDB4]/20 max-w-3xl mx-auto">
            <p className="text-[#2A5D67] font-medium mb-3 text-lg">
              Tutti i piani includono crediti pay-as-you-go per uso oltre i
              limiti
            </p>
            <p className="text-[#1E293B] text-base">
              Nessuna carta di credito richiesta per iniziare &bull; Upgrade in
              qualsiasi momento &bull; Supporto clienti dedicato
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
