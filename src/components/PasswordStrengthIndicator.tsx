import React from 'react';
import { Check, X } from 'lucide-react';
import { validatePassword, getPasswordStrengthLabel, getPasswordStrengthColor } from '../lib/validation';

interface PasswordStrengthIndicatorProps {
  password: string;
  className?: string;
}

export function PasswordStrengthIndicator({ password, className = '' }: PasswordStrengthIndicatorProps) {
  const validation = validatePassword(password);
  const strengthLabel = getPasswordStrengthLabel(password);
  const strengthColor = getPasswordStrengthColor(password);

  if (!password) {
    return null;
  }

  const requirements = [
    { key: 'length', label: 'At least 8 characters', check: validation.checks.length },
    { key: 'uppercase', label: 'One uppercase letter', check: validation.checks.uppercase },
    { key: 'lowercase', label: 'One lowercase letter', check: validation.checks.lowercase },
    { key: 'number', label: 'One number', check: validation.checks.number },
    { key: 'specialChar', label: 'One special character', check: validation.checks.specialChar },
  ];

  return (
    <div className={`mt-2 ${className}`}>
      {/* Strength Label */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-600">Password strength:</span>
        <span className={`text-sm font-medium ${strengthColor}`}>
          {strengthLabel}
        </span>
      </div>

      {/* Strength Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${
            validation.checks.length && validation.checks.uppercase && validation.checks.lowercase && validation.checks.number && validation.checks.specialChar
              ? 'bg-green-500'
              : validation.checks.length && (validation.checks.uppercase || validation.checks.lowercase) && (validation.checks.number || validation.checks.specialChar)
              ? 'bg-blue-500'
              : validation.checks.length && (validation.checks.uppercase || validation.checks.lowercase)
              ? 'bg-yellow-500'
              : validation.checks.length
              ? 'bg-orange-500'
              : 'bg-red-500'
          }`}
          style={{ 
            width: `${(Object.values(validation.checks).filter(Boolean).length / 5) * 100}%` 
          }}
        />
      </div>

      {/* Requirements List */}
      <div className="space-y-1">
        {requirements.map(({ key, label, check }) => (
          <div key={key} className="flex items-center space-x-2 text-sm">
            {check ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <X className="w-4 h-4 text-gray-400" />
            )}
            <span className={check ? 'text-green-600' : 'text-gray-500'}>
              {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}