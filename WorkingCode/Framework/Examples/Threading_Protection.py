'''A few things to keep in mind when operating with threads, especially within this Framework:
    * Objects should operate in a thread safe manner.
        - Resources that can be edited/accessed by multiple threads should ensure that those resources are
        protected by a threading lock. (Threading.Lock or Threading.RLock) See Examples.Threading_Protection for more in depth information.
    * Be sure of which threads are accessing what resources at what time (and from which module).
        - IE two separate threads could be accessing one module's resource at once. Sometimes this could break things, especially mutable objects.
    * certain modules and libraries are not thread safe (though these days most things are)
        - IE QT doesn't work in some cases with multithreading. QT methods should only be called in the Qt main event loop.
    * Accessing another thread's resources
        - 'accept' Methods
    * Starting and ending threads
        - Base classes methods.
        - Freeing resources when done.
    * Methods necessary to implement.'''