"use client";

import { Star } from "lucide-react";

export function TestimonialsSection() {
  const testimonials = [
    {
      quote:
        "Prima perdevo ore cercando circolari. Ora ho tutto in 3 secondi. PratikoAI ha rivoluzionato il mio modo di lavorare.",
      author: "Marco Rossi",
      company: "Studio Rossi & Associati",
      rating: 5,
    },
    {
      quote:
        "Finalmente posso dedicare più tempo ai clienti invece di cercare normative. L&apos;aggiornamento automatico è fantastico.",
      author: "Giulia Bianchi",
      company: "Consulente Fiscale",
      rating: 5,
    },
    {
      quote:
        "Ho ridotto i costi degli abbonamenti del 70% e ottengo risposte più precise. Uno strumento indispensabile.",
      author: "Andrea Conti",
      company: "Studio Conti",
      rating: 5,
    },
    {
      quote:
        "La possibilità di analizzare documenti in tempo reale mi ha fatto risparmiare ore di lavoro ogni settimana.",
      author: "Francesca Marino",
      company: "Commercialista",
      rating: 5,
    },
  ];

  return (
    <section className="py-20 lg:py-32 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-6">
            Cosa dicono i professionisti
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Oltre 50 commercialisti hanno già trasformato il loro modo di
            lavorare con PratikoAI
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-8">
          {testimonials.map((testimonial, index) => (
            <div
              key={index}
              className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 hover:shadow-lg transition-shadow duration-300"
            >
              {/* Quote */}
              <div className="mb-6">
                <div className="text-4xl text-blue-600 mb-4">&ldquo;</div>
                <p className="text-lg text-gray-700 leading-relaxed">
                  {testimonial.quote}
                </p>
              </div>

              {/* Rating */}
              <div className="flex items-center space-x-1 mb-4">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <Star
                    key={i}
                    className="w-5 h-5 fill-yellow-400 text-yellow-400"
                  />
                ))}
              </div>

              {/* Author */}
              <div className="border-t border-gray-100 pt-6">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gradient-primary rounded-full flex items-center justify-center">
                    <span className="text-white font-semibold text-sm">
                      {testimonial.author.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">
                      {testimonial.author}
                    </div>
                    <div className="text-sm text-gray-600">
                      {testimonial.company}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom Stats */}
        <div className="mt-16 text-center">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="text-3xl font-bold text-blue-600 mb-2">50+</div>
              <div className="text-gray-600">Professionisti attivi</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-green-600 mb-2">95%</div>
              <div className="text-gray-600">Soddisfazione cliente</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-600 mb-2">10h</div>
              <div className="text-gray-600">Risparmiate a settimana</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}