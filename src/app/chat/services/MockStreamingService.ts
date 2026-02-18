interface MockStreamingServiceProps {
  onChunk: (chunk: string) => void
  onComplete: () => void
}

/**
 * MockStreamingService simulates backend streaming behavior
 * 
 * Features:
 * - Realistic 1-2 second initial delay
 * - Progressive HTML chunk building
 * - Preserves HTML structure integrity
 * - Configurable streaming intervals
 * - Proper cleanup and error handling
 */
export class MockStreamingService {
  private onChunk: (chunk: string) => void
  private onComplete: () => void
  private timeouts: NodeJS.Timeout[] = []
  private isStopped = false

  constructor({ onChunk, onComplete }: MockStreamingServiceProps) {
    this.onChunk = onChunk
    this.onComplete = onComplete
  }

  /**
   * Start streaming a response with realistic timing
   */
  streamResponse(message: string): void {
    this.isStopped = false
    this.clearTimeouts()

    if (!message) {
      this.scheduleCallback(() => this.onComplete(), 100)
      return
    }

    // Initial delay: 1-2 seconds to simulate processing
    const initialDelay = 1000 + Math.random() * 1000
    
    this.scheduleCallback(() => {
      if (this.isStopped) return
      this.startChunkedStreaming(message)
    }, initialDelay)
  }

  /**
   * Stop streaming and clear all timeouts
   */
  stop(): void {
    this.isStopped = true
    this.clearTimeouts()
  }

  /**
   * Stream message in progressive chunks
   */
  private startChunkedStreaming(fullMessage: string): void {
    const textContent = this.extractTextContent(fullMessage)
    const totalLength = textContent.length
    
    if (totalLength === 0) {
      this.scheduleCallback(() => this.safeCall(() => this.onComplete()), 100)
      return
    }

    let currentLength = 0
    const chunkSize = Math.max(1, Math.floor(totalLength / 10)) // ~10 chunks
    
    const streamNextChunk = () => {
      if (this.isStopped) return

      currentLength = Math.min(currentLength + chunkSize, totalLength)
      const chunk = this.reconstructHTML(fullMessage, currentLength)
      
      this.safeCall(() => this.onChunk(chunk))

      if (currentLength >= totalLength) {
        // Ensure final chunk is complete
        this.scheduleCallback(() => {
          if (!this.isStopped) {
            this.safeCall(() => this.onChunk(fullMessage))
            this.safeCall(() => this.onComplete())
          }
        }, 200)
      } else {
        // Schedule next chunk
        const delay = 150 + Math.random() * 100 // 150-250ms between chunks
        this.scheduleCallback(streamNextChunk, delay)
      }
    }

    streamNextChunk()
  }

  /**
   * Extract visible text content from HTML
   */
  private extractTextContent(html: string): string {
    return html.replace(/<[^>]*>/g, '')
  }

  /**
   * Reconstruct HTML with partial text content
   */
  private reconstructHTML(html: string, targetLength: number): string {
    if (targetLength <= 0) {
      // Return HTML structure with empty content
      return html.replace(/>([^<]*)</g, (match, content) => {
        return '><'
      }).replace(/>([^<]*)$/, '>')
    }
    
    let textIndex = 0
    let result = ''
    let i = 0
    
    while (i < html.length) {
      if (html[i] === '<') {
        // Copy entire HTML tag
        const tagEnd = html.indexOf('>', i)
        if (tagEnd !== -1) {
          result += html.substring(i, tagEnd + 1)
          i = tagEnd + 1
        } else {
          // Malformed HTML - copy character
          result += html[i]
          i++
        }
      } else {
        // Handle text content
        if (textIndex < targetLength) {
          result += html[i]
          textIndex++
        }
        i++
      }
    }
    
    return result
  }

  /**
   * Schedule a callback with timeout tracking
   */
  private scheduleCallback(callback: () => void, delay: number): void {
    const timeout = setTimeout(() => {
      this.removeTimeout(timeout)
      callback()
    }, delay)
    
    this.timeouts.push(timeout)
  }

  /**
   * Safely call a function with error handling
   */
  private safeCall(fn: () => void): void {
    try {
      fn()
    } catch (error) {
      console.warn('MockStreamingService callback error:', error)
    }
  }

  /**
   * Remove a timeout from tracking
   */
  private removeTimeout(timeout: NodeJS.Timeout): void {
    const index = this.timeouts.indexOf(timeout)
    if (index > -1) {
      this.timeouts.splice(index, 1)
    }
  }

  /**
   * Clear all tracked timeouts
   */
  private clearTimeouts(): void {
    this.timeouts.forEach(timeout => clearTimeout(timeout))
    this.timeouts = []
  }
}