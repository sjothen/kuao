(define hanoi
  (lambda (n)
    (if (= n 1)
        1
        (+ (* 2 (hanoi (- n 1))) 1))))

(display (hanoi 30))
(display "\n")
