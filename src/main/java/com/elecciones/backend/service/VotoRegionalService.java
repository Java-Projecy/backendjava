package com.elecciones.backend.service;

import com.elecciones.backend.model.VotoRegional;
import com.elecciones.backend.repository.VotoRegionalRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class VotoRegionalService {

    private final VotoRegionalRepository repository;

    public VotoRegionalService(VotoRegionalRepository repository) {
        this.repository = repository;
    }

    public List<VotoRegional> getAll() {
        return repository.findAll();
    }

    public Optional<VotoRegional> getById(UUID id) {
        return repository.findById(id);
    }

    public VotoRegional save(VotoRegional voto) {
        return repository.save(voto);
    }

    public void delete(UUID id) {
        repository.deleteById(id);
    }
}
