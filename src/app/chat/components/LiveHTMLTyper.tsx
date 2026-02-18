'use client'
import React, { useEffect, useMemo, useRef, useState } from 'react'

/**
 * LiveHTMLTyper
 * - Reveals only the new SUFFIX of the incoming HTML string with a typing effect
 * - If the suffix contains `<` (i.e. tags), we snap to full HTML to avoid breaking tags
 * - No duplication: we keep track of last committed length
 */
export default function LiveHTMLTyper({
                                          html,
                                          typing = true,
                                          cps = 60,             // chars per second
                                          className = '',
                                      }: {
    html: string
    typing?: boolean
    cps?: number
    className?: string
}) {
    const [rendered, setRendered] = useState<string>('')
    const timerRef = useRef<number | null>(null)
    const lastLenRef = useRef<number>(0)

    // normalize null/undefined
    const safeHtml = html || ''

    // Compute the new suffix (what arrived since last commit)
    const { prev, suffix } = useMemo(() => {
        const prevLen = lastLenRef.current
        const nextLen = safeHtml.length
        const delta = nextLen > prevLen ? safeHtml.slice(prevLen) : ''
        return { prev: safeHtml.slice(0, prevLen), suffix: delta }
    }, [safeHtml])

    // Kick typing whenever a new suffix arrives
    useEffect(() => {
        // If nothing new, ensure we're aligned (e.g. after remounts)
        if (!suffix) {
            if (rendered !== safeHtml) {
                setRendered(safeHtml)
                lastLenRef.current = safeHtml.length
            }
            return
        }

        // If suffix contains tags, snap immediately to full to avoid broken HTML
        if (!typing || /<[^>]*>/.test(suffix)) {
            setRendered(safeHtml)
            lastLenRef.current = safeHtml.length
            return
        }

        // Typing animation for plain-text suffix
        const step = Math.max(1, Math.round(cps / 10)) // small burst for smoothness
        const interval = 1000 / cps

        let i = 0
        const tick = () => {
            // Append next chunk of the suffix
            i += step
            const next = prev + suffix.slice(0, i)
            setRendered(next)

            if (i >= suffix.length) {
                // Commit to canonical value at the end (important)
                setRendered(safeHtml)
                lastLenRef.current = safeHtml.length
                timerRef.current = null
                return
            }
            timerRef.current = window.setTimeout(tick, interval)
        }

        // start
        if (timerRef.current) window.clearTimeout(timerRef.current)
        timerRef.current = window.setTimeout(tick, interval)

        return () => {
            if (timerRef.current) {
                window.clearTimeout(timerRef.current)
                timerRef.current = null
            }
        }
    }, [suffix, prev, cps, typing, safeHtml, rendered])

    // Keep lastLen in sync if upstream resets/rewinds
    useEffect(() => {
        if (safeHtml.length < lastLenRef.current) {
            lastLenRef.current = safeHtml.length
            setRendered(safeHtml)
        }
    }, [safeHtml])

    return (
        <div
            className={className}
            // We feed the progressively revealed HTML
            dangerouslySetInnerHTML={{ __html: rendered }}
        />
    )
}
