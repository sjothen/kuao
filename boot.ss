(define (reverse xs)
  (define (helper acc xs)
    (if (null? xs)
        acc
        (helper (cons (car xs) acc)
                (cdr xs))))
  (helper '() xs))

(define (map f xs)
  (define (helper f acc xs)
    (if (null? xs)
        (reverse acc)
        (helper f
                (cons (f (car xs)) acc)
                (cdr xs))))
  (helper f '() xs))

;; print a newline
(define (newline)
  (display "\n"))
