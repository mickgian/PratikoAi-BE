'use client';

import { motion } from 'motion/react';
import {
  Edit,
  Send,
  Check,
  Trash2,
  Mail,
  MessageCircle,
  FileText,
  Calendar,
  User,
  Eye,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import type {
  Communication,
  CommunicationStatus,
  CommunicationChannel,
} from '../types';

interface ComunicazioneCardProps {
  communication: Communication;
  isSelected: boolean;
  animationDelay: number;
  onSelect: (id: string) => void;
  onEdit: (communication: Communication) => void;
  onSubmitForReview: (id: string) => void;
  onApprove: (id: string) => void;
  onSend: (id: string) => void;
  onDelete: (id: string) => void;
}

function getStatusBadge(status: CommunicationStatus) {
  const configs: Record<
    CommunicationStatus,
    { label: string; className: string }
  > = {
    bozza: {
      label: 'Bozza',
      className: 'bg-gray-100 text-gray-700 border-gray-300',
    },
    in_revisione: {
      label: 'In Revisione',
      className: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    },
    approvata: {
      label: 'Approvata',
      className: 'bg-green-100 text-green-700 border-green-300',
    },
    inviata: {
      label: 'Inviata',
      className: 'bg-blue-100 text-blue-700 border-blue-300',
    },
  };
  const config = configs[status];
  return <Badge className={`${config.className} border`}>{config.label}</Badge>;
}

function getChannelIcon(channel: CommunicationChannel) {
  return channel === 'email' ? (
    <Mail className="w-4 h-4 text-[#2A5D67]" />
  ) : (
    <MessageCircle className="w-4 h-4 text-[#2A5D67]" />
  );
}

export function ComunicazioneCard({
  communication,
  isSelected,
  animationDelay,
  onSelect,
  onEdit,
  onSubmitForReview,
  onApprove,
  onSend,
  onDelete,
}: ComunicazioneCardProps) {
  const formattedDate = new Date(communication.createdDate).toLocaleDateString(
    'it-IT',
    {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }
  );

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ delay: animationDelay }}
      className={`bg-white rounded-lg shadow-sm border transition-all hover:shadow-md ${
        isSelected
          ? 'border-[#2A5D67] ring-2 ring-[#2A5D67]/20'
          : 'border-[#C4BDB4]/20'
      }`}
    >
      <div className="p-6">
        <div className="flex items-start space-x-4">
          <div className="pt-1">
            <Checkbox
              checked={isSelected}
              onCheckedChange={() => onSelect(communication.id)}
              className="border-[#C4BDB4]"
            />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-[#2A5D67] mb-1">
                  {communication.subject}
                </h3>
                <div className="flex flex-wrap items-center gap-3 text-sm text-[#1E293B]">
                  <div className="flex items-center space-x-1">
                    <User className="w-4 h-4" />
                    <span>{communication.clientName}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    {getChannelIcon(communication.channel)}
                    <span className="capitalize">{communication.channel}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <FileText className="w-4 h-4" />
                    <span>{communication.normativaReference}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-4 h-4" />
                    <span>{formattedDate}</span>
                  </div>
                </div>
              </div>
              <div className="ml-4">{getStatusBadge(communication.status)}</div>
            </div>

            <p className="text-sm text-[#1E293B] line-clamp-2 mb-4">
              {communication.body}
            </p>

            <div className="flex items-center space-x-2">
              <Button
                onClick={() => onEdit(communication)}
                size="sm"
                variant="outline"
                className="text-[#2A5D67] border-[#2A5D67] hover:bg-[#F8F5F1]"
              >
                <Edit className="w-4 h-4 mr-1" />
                Modifica
              </Button>

              {communication.status === 'bozza' && (
                <Button
                  onClick={() => onSubmitForReview(communication.id)}
                  size="sm"
                  className="bg-yellow-600 hover:bg-yellow-700 text-white"
                >
                  <Clock className="w-4 h-4 mr-1" />
                  Invia a Revisione
                </Button>
              )}

              {communication.status === 'in_revisione' && (
                <Button
                  onClick={() => onApprove(communication.id)}
                  size="sm"
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  <Check className="w-4 h-4 mr-1" />
                  Approva
                </Button>
              )}

              {communication.status === 'approvata' && (
                <Button
                  onClick={() => onSend(communication.id)}
                  size="sm"
                  className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                >
                  <Send className="w-4 h-4 mr-1" />
                  <span className="font-bold">Invia</span>
                </Button>
              )}

              {communication.status === 'inviata' && (
                <Button
                  onClick={() => onEdit(communication)}
                  size="sm"
                  variant="outline"
                >
                  <Eye className="w-4 h-4 mr-1" />
                  Visualizza
                </Button>
              )}

              <Button
                onClick={() => onDelete(communication.id)}
                size="sm"
                variant="ghost"
                className="text-red-600 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
