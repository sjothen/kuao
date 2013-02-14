(define (caar xs) (car (car xs)))
(define (cadr xs) (car (cdr xs)))

(define (caaar xs) (car (car (car xs))))
(define (caadr xs) (car (car (cdr xs))))
(define (cadar xs) (car (cdr (car xs))))
(define (caddr xs) (car (cdr (cdr xs))))
(define (cdaar xs) (cdr (car (car xs))))
(define (cdadr xs) (cdr (car (cdr xs))))
(define (cddar xs) (cdr (cdr (car xs))))
(define (cdddr xs) (cdr (cdr (cdr xs))))

(define (caaaar xs) (car (car (car (car xs)))))
(define (caaadr xs) (car (car (car (cdr xs)))))
(define (caadar xs) (car (car (cdr (car xs)))))
(define (caaddr xs) (car (car (cdr (cdr xs)))))
(define (cadaar xs) (car (cdr (car (car xs)))))
(define (cadadr xs) (car (cdr (car (cdr xs)))))
(define (caddar xs) (car (cdr (cdr (car xs)))))
(define (cadddr xs) (car (cdr (cdr (cdr xs)))))
(define (cdaaar xs) (cdr (car (car (car xs)))))
(define (cdaadr xs) (cdr (car (car (cdr xs)))))
(define (cdadar xs) (cdr (car (cdr (car xs)))))
(define (cdaddr xs) (cdr (car (cdr (cdr xs)))))
(define (cddaar xs) (cdr (cdr (car (car xs)))))
(define (cddadr xs) (cdr (cdr (car (cdr xs)))))
(define (cdddar xs) (cdr (cdr (cdr (car xs)))))
(define (cddddr xs) (cdr (cdr (cdr (cdr xs)))))

(define (list . args)
  args)

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

(define-macro (when condition . body)
  `(if ,condition
       (begin ,@body)))

(define-macro (unless condition . body)
  `(when (not ,condition) ,@body))

(define-macro (let clauses . body)
  `((lambda ,(map car clauses) ,@body) ,@(map cadr clauses)))

(define (foldl f z xs)
  (if (null? xs)
      z
      (foldl f (f z (car xs)) (cdr xs))))

(define fold foldl)
(define reduce foldl)

(define (length lst)
  (fold (lambda (x y) (+ x 1)) 0 lst))

(define (foldr f z xs)
  (if (null? xs)
      z
      (f (car xs) (foldr f z (cdr xs)))))

(define (filter p? xs)
  (foldr (lambda (x y)
           (if (p? x)
               (cons x y)
               y))
         '()
         xs))
