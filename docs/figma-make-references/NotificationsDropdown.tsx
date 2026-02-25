"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Bell,
  Clock,
  Target,
  CheckCircle,
  BookOpen,
  X,
  Check,
} from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

interface Notification {
  id: string;
  type: "scadenza" | "match" | "comunicazione" | "normativa";
  title: string;
  description: string;
  timestamp: Date;
  read: boolean;
}

const mockNotifications: Notification[] = [
  {
    id: "1",
    type: "scadenza",
    title: "Scadenza Imminente",
    description: "Dichiarazione IVA trimestrale - Cliente: Rossi S.r.l.",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    read: false,
  },
  {
    id: "2",
    type: "match",
    title: "Nuovo Match Normativo",
    description: "3 nuovi match per il cliente Bianchi & Partners",
    timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000), // 5 hours ago
    read: false,
  },
  {
    id: "3",
    type: "comunicazione",
    title: "Comunicazione Approvata",
    description: "La comunicazione per Verdi S.p.A. è stata approvata",
    timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000), // 8 hours ago
    read: true,
  },
  {
    id: "4",
    type: "normativa",
    title: "Aggiornamento Normativo",
    description: "Nuova circolare Agenzia delle Entrate n. 5/2025",
    timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), // 1 day ago
    read: false,
  },
  {
    id: "5",
    type: "scadenza",
    title: "Scadenza Imminente",
    description: "Versamento F24 - Cliente: Neri & Associati",
    timestamp: new Date(
      Date.now() - 1 * 24 * 60 * 60 * 1000 - 3 * 60 * 60 * 1000,
    ), // 1 day + 3 hours ago
    read: true,
  },
  {
    id: "6",
    type: "match",
    title: "Nuovo Match Normativo",
    description: "5 nuovi match rilevanti per Ferrari S.r.l.",
    timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
    read: true,
  },
  {
    id: "7",
    type: "normativa",
    title: "Aggiornamento Normativo",
    description: "Decreto-legge fiscale approvato in Gazzetta Ufficiale",
    timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), // 5 days ago
    read: true,
  },
];

const getNotificationIcon = (type: Notification["type"]) => {
  switch (type) {
    case "scadenza":
      return { icon: Clock, color: "text-red-500", bg: "bg-red-50" };
    case "match":
      return { icon: Target, color: "text-orange-500", bg: "bg-orange-50" };
    case "comunicazione":
      return { icon: CheckCircle, color: "text-green-500", bg: "bg-green-50" };
    case "normativa":
      return { icon: BookOpen, color: "text-blue-500", bg: "bg-blue-50" };
  }
};

const getTimeAgo = (date: Date): string => {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);

  if (hours < 1) {
    const minutes = Math.floor(diff / (1000 * 60));
    return `${minutes} minuti fa`;
  }
  if (hours < 24) {
    return `${hours} ${hours === 1 ? "ora" : "ore"} fa`;
  }
  if (days === 1) {
    return "Ieri";
  }
  if (days < 7) {
    return `${days} giorni fa`;
  }
  return date.toLocaleDateString("it-IT", { day: "numeric", month: "short" });
};

const groupNotificationsByTime = (notifications: Notification[]) => {
  const now = new Date();
  const oggi: Notification[] = [];
  const ieri: Notification[] = [];
  const questaSettimana: Notification[] = [];

  notifications.forEach((notification) => {
    const diff = now.getTime() - notification.timestamp.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (hours < 24) {
      oggi.push(notification);
    } else if (days === 1 || (days < 2 && hours < 48)) {
      ieri.push(notification);
    } else if (days < 7) {
      questaSettimana.push(notification);
    }
  });

  return { oggi, ieri, questaSettimana };
};

interface NotificationsDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  onViewAll?: () => void;
}

export function NotificationsDropdown({
  isOpen,
  onClose,
  onViewAll,
}: NotificationsDropdownProps) {
  const [notifications, setNotifications] =
    useState<Notification[]>(mockNotifications);

  const unreadCount = notifications.filter((n) => !n.read).length;
  const { oggi, ieri, questaSettimana } =
    groupNotificationsByTime(notifications);

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40"
            onClick={onClose}
          />

          {/* Dropdown Panel */}
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-[420px] z-50"
          >
            <Card className="shadow-2xl border-[#C4BDB4]/30 overflow-hidden">
              {/* Header */}
              <div className="bg-gradient-to-r from-[#2A5D67] to-[#1E293B] px-6 py-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Bell className="w-5 h-5 text-white" />
                    <h3 className="font-semibold text-white">Notifiche</h3>
                    {unreadCount > 0 && (
                      <span className="bg-[#D4A574] text-white text-xs font-bold px-2 py-0.5 rounded-full">
                        {unreadCount}
                      </span>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="text-white hover:bg-white/10 -mr-2"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={markAllAsRead}
                    className="text-white/90 hover:bg-white/10 text-xs h-7 px-3"
                  >
                    <Check className="w-3 h-3 mr-1.5" />
                    Segna tutte come lette
                  </Button>
                )}
              </div>

              {/* Notifications List */}
              <div className="max-h-[500px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="px-6 py-12 text-center">
                    <Bell className="w-12 h-12 mx-auto text-[#C4BDB4] mb-3" />
                    <p className="text-[#1E293B]/60">Nessuna notifica</p>
                  </div>
                ) : (
                  <div className="divide-y divide-[#C4BDB4]/20">
                    {/* Oggi */}
                    {oggi.length > 0 && (
                      <div className="px-6 py-4">
                        <h4 className="text-xs font-semibold text-[#2A5D67] mb-3 uppercase tracking-wider">
                          Oggi
                        </h4>
                        <div className="space-y-3">
                          {oggi.map((notification) => (
                            <NotificationItem
                              key={notification.id}
                              notification={notification}
                              onMarkAsRead={markAsRead}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Ieri */}
                    {ieri.length > 0 && (
                      <div className="px-6 py-4">
                        <h4 className="text-xs font-semibold text-[#2A5D67] mb-3 uppercase tracking-wider">
                          Ieri
                        </h4>
                        <div className="space-y-3">
                          {ieri.map((notification) => (
                            <NotificationItem
                              key={notification.id}
                              notification={notification}
                              onMarkAsRead={markAsRead}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Questa Settimana */}
                    {questaSettimana.length > 0 && (
                      <div className="px-6 py-4">
                        <h4 className="text-xs font-semibold text-[#2A5D67] mb-3 uppercase tracking-wider">
                          Questa Settimana
                        </h4>
                        <div className="space-y-3">
                          {questaSettimana.map((notification) => (
                            <NotificationItem
                              key={notification.id}
                              notification={notification}
                              onMarkAsRead={markAsRead}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Footer */}
              {notifications.length > 0 && (
                <div className="px-6 py-3 bg-[#F8F5F1] border-t border-[#C4BDB4]/20">
                  <Button
                    variant="ghost"
                    onClick={onViewAll}
                    className="w-full text-[#2A5D67] hover:bg-white font-medium text-sm"
                  >
                    Vedi tutte le notifiche
                  </Button>
                </div>
              )}
            </Card>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function NotificationItem({
  notification,
  onMarkAsRead,
}: {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
}) {
  const { icon: Icon, color, bg } = getNotificationIcon(notification.type);

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={`flex items-start space-x-3 p-3 rounded-lg transition-colors ${
        notification.read
          ? "bg-white hover:bg-[#F8F5F1]/50"
          : "bg-[#F8F5F1] hover:bg-[#F8F5F1]/70"
      } group cursor-pointer`}
    >
      {/* Icon */}
      <div className={`${bg} rounded-lg p-2 flex-shrink-0`}>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between mb-1">
          <h5
            className={`text-sm font-medium ${
              notification.read ? "text-[#1E293B]/70" : "text-[#1E293B]"
            }`}
          >
            {notification.title}
          </h5>
          {!notification.read && (
            <div className="w-2 h-2 bg-[#2A5D67] rounded-full flex-shrink-0 mt-1.5" />
          )}
        </div>
        <p
          className={`text-xs mb-2 ${
            notification.read ? "text-[#1E293B]/50" : "text-[#1E293B]/70"
          }`}
        >
          {notification.description}
        </p>
        <div className="flex items-center justify-between">
          <span className="text-xs text-[#1E293B]/40">
            {getTimeAgo(notification.timestamp)}
          </span>
          {!notification.read && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onMarkAsRead(notification.id);
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-[#2A5D67] hover:bg-white h-6 px-2 text-xs"
            >
              <Check className="w-3 h-3 mr-1" />
              Letta
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
