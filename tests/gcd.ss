(define remainder
  (lambda (a b)
    (if (< a b)
        a
        (remainder (- a b) b))))

(define gcd
  (lambda (x y)
    (if (= y 0)
        x
        (gcd y (remainder x y)))))

(define println
  (lambda (x)
    (display x "\n")))

(println (remainder 11 10))
(println (gcd 27 9))
(println (gcd 259 111))
